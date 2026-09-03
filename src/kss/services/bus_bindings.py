"""Materialize BUS indexes from the current knxproj snapshot.

PA: ``individual_address_loaded`` and a real ``last_downloaded``.
GA: ``communication_part_loaded``, real ``last_downloaded``, and currently
linked CO↔GA edges (``linked=true``). Sentinel LastDownload is never stored.
Same PK skips; missing entities are not unlinked. Not a 3API resource.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.bus_bindings import BusGaBinding, BusPaBinding
from kss.models.datapoint import Datapoint
from kss.models.device import CommObject, CommObjectDatapoint, Device
from kss.models.installation import Installation


def upsert_bus_bindings_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    del fallback_last_modified
    devices_raw = project.get("devices")
    if not isinstance(devices_raw, Mapping):
        return
    devices_by_ets = _devices_by_ets_id(session, installation.id)
    current_group_address = _current_group_addresses(session, installation.id)
    linked_gas_by_device = _current_linked_group_addresses(
        session, installation.id, current_group_address
    )
    for raw in devices_raw.values():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _device_ets_id(raw.get("ets_id"), raw.get("identifier"))
        if not ets_id:
            continue
        device = devices_by_ets.get(ets_id)
        if device is None or not device.versions:
            continue
        version = max(device.versions, key=lambda item: item.last_modified)
        downloaded = version.last_downloaded
        if downloaded is None:
            continue
        downloaded = _aware_utc(downloaded)
        if version.individual_address_loaded is True:
            _ensure_pa_binding(
                session,
                installation_id=installation.id,
                individual_address=version.individual_address,
                last_downloaded=downloaded,
                device_id=device.id,
            )
        if version.communication_part_loaded is True:
            for group_address in linked_gas_by_device.get(device.id, ()):
                _ensure_ga_binding(
                    session,
                    installation_id=installation.id,
                    group_address=group_address,
                    device_id=device.id,
                    last_downloaded=downloaded,
                )
    session.flush()


def _ensure_pa_binding(
    session: Session,
    *,
    installation_id: UUID,
    individual_address: str | None,
    last_downloaded: datetime,
    device_id: UUID,
) -> None:
    address = (individual_address or "").strip()
    if not address:
        return
    existing = session.get(
        BusPaBinding, (installation_id, address, last_downloaded)
    )
    if existing is not None:
        return
    session.add(
        BusPaBinding(
            installation_id=installation_id,
            individual_address=address,
            last_downloaded=last_downloaded,
            device_id=device_id,
        )
    )


def _ensure_ga_binding(
    session: Session,
    *,
    installation_id: UUID,
    group_address: int,
    device_id: UUID,
    last_downloaded: datetime,
) -> None:
    if group_address < 0 or group_address > 65535:
        return
    existing = session.get(
        BusGaBinding, (installation_id, group_address, device_id, last_downloaded)
    )
    if existing is not None:
        return
    session.add(
        BusGaBinding(
            installation_id=installation_id,
            group_address=group_address,
            device_id=device_id,
            last_downloaded=last_downloaded,
        )
    )


def _devices_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, Device]:
    rows = session.scalars(
        select(Device)
        .where(Device.installation_id == installation_id)
        .options(selectinload(Device.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _current_group_addresses(
    session: Session, installation_id: UUID
) -> dict[UUID, int]:
    rows = session.scalars(
        select(Datapoint)
        .where(Datapoint.installation_id == installation_id)
        .options(selectinload(Datapoint.versions))
    ).all()
    mapping: dict[UUID, int] = {}
    for datapoint in rows:
        if not datapoint.versions:
            continue
        current = max(datapoint.versions, key=lambda item: item.last_modified)
        if current.group_address is None:
            continue
        mapping[datapoint.id] = current.group_address
    return mapping


def _current_linked_group_addresses(
    session: Session,
    installation_id: UUID,
    current_group_address: dict[UUID, int],
) -> dict[UUID, set[int]]:
    comm_objects = session.scalars(
        select(CommObject)
        .join(Device, Device.id == CommObject.device_id)
        .where(Device.installation_id == installation_id)
    ).all()
    device_by_co = {row.id: row.device_id for row in comm_objects}
    if not device_by_co:
        return {}
    edges = session.scalars(
        select(CommObjectDatapoint).where(
            CommObjectDatapoint.comm_object_id.in_(device_by_co)
        )
    ).all()
    current_edge: dict[tuple[UUID, UUID], CommObjectDatapoint] = {}
    for edge in edges:
        key = (edge.comm_object_id, edge.datapoint_id)
        previous = current_edge.get(key)
        if previous is None or edge.last_modified > previous.last_modified:
            current_edge[key] = edge
    by_device: dict[UUID, set[int]] = {}
    for edge in current_edge.values():
        if not edge.linked:
            continue
        group_address = current_group_address.get(edge.datapoint_id)
        if group_address is None:
            continue
        device_id = device_by_co.get(edge.comm_object_id)
        if device_id is None:
            continue
        by_device.setdefault(device_id, set()).add(group_address)
    return by_device


def _device_ets_id(explicit: object, identifier: object) -> str | None:
    value = _optional_str(explicit)
    if value:
        return value.rsplit("_", 1)[-1] or None
    ident = _optional_str(identifier)
    if not ident:
        return None
    return ident.rsplit("_", 1)[-1] or None


def _optional_str(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
