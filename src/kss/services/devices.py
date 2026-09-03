"""Upsert Device from knxproj parse output (same PATCH as Installation).

Identity is ``ets_id`` (``DI-n``), never the devices dict key (individual address).
Does not persist trades. Channel/Folder/CO run in
``device_parts`` after this upsert. BUS indexes run after CO↔GA. ``location_id`` comes from Space device
refs (IA); ``segment_id`` from ``segment_ets_id``. Missing keys skip writes;
missing entities are not unlinked.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import COMPLETION_STATUS_VALUES
from kss.models.device import Device, DeviceVersion
from kss.models.installation import Installation
from kss.models.location import Location
from kss.models.master import MasterProduct
from kss.models.topology import Segment
from kss.services.knxproj import KnxprojImportError, parse_ets_datetime
from kss.services.temporal import item_at, pairs_at

DEVICE_SEMANTIC_FIELDS = (
    "title",
    "description",
    "comment",
    "last_downloaded",
    "serial_number",
    "individual_address",
    "firmware_version",
    "hardware_version",
    "completion_status",
    "communication_part_loaded",
    "individual_address_loaded",
    "application_program_loaded",
    "parameters_loaded",
    "medium_config_loaded",
    "product_ref",
    "hardware_program_ref",
    "application_program_ref",
    "bus_current",
    "installation_hints",
    "at_type",
    "location_id",
    "segment_id",
)


def current_device_pairs(session: Session) -> list[tuple[Device, DeviceVersion]]:
    devices = session.scalars(
        select(Device).options(selectinload(Device.versions)).order_by(Device.id)
    ).all()
    return pairs_at(devices)


def get_current_device(
    session: Session, device_id: UUID
) -> tuple[Device, DeviceVersion] | None:
    device = session.get(
        Device, device_id, options=(selectinload(Device.versions),)
    )
    found = item_at(device)
    if found is None:
        return None
    return found[0], found[1]


def current_devices_for_location(
    session: Session, location_id: UUID
) -> list[tuple[Device, DeviceVersion]]:
    return [
        (device, version)
        for device, version in current_device_pairs(session)
        if version.location_id == location_id
    ]


def products_for_versions(
    session: Session, versions: list[DeviceVersion]
) -> dict[str, MasterProduct]:
    refs = {version.product_ref for version in versions if version.product_ref}
    if not refs:
        return {}
    rows = session.scalars(
        select(MasterProduct).where(MasterProduct.knx_id.in_(refs))
    ).all()
    return {row.knx_id: row for row in rows}


def upsert_devices_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    devices_raw = project.get("devices")
    if not isinstance(devices_raw, Mapping):
        return
    fallback = _aware_utc(fallback_last_modified)
    by_ets = _devices_by_ets_id(session, installation.id)
    locations_by_ets = _locations_by_ets_id(session, installation.id)
    segments_by_ets = _segments_by_ets_id(session, installation.id)
    ia_to_location = _ia_to_location_id(project.get("locations"), locations_by_ets)

    rows: list[tuple[Mapping[str, object], str, str | None]] = []
    new_identities: list[Device] = []
    for ia, raw in devices_raw.items():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _ets_id(raw.get("ets_id"), raw.get("identifier"))
        if not ets_id:
            continue
        individual_address = _optional_str(raw.get("individual_address")) or (
            ia if isinstance(ia, str) else None
        )
        rows.append((raw, ets_id, individual_address))
        if ets_id in by_ets:
            continue
        device = Device(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(device)
        by_ets[ets_id] = device
        new_identities.append(device)
    if new_identities:
        session.flush()

    for raw, ets_id, individual_address in rows:
        device = by_ets[ets_id]
        location_id = None
        if individual_address:
            location_id = ia_to_location.get(individual_address)
        segment_id = None
        segment_ets_id = _ets_id(raw.get("segment_ets_id"), None)
        if segment_ets_id:
            segment = segments_by_ets.get(segment_ets_id)
            if segment is not None:
                segment_id = segment.id
        _upsert_device_version(
            session,
            device,
            raw,
            individual_address=individual_address,
            location_id=location_id,
            segment_id=segment_id,
            fallback=fallback,
        )
    session.flush()


def _upsert_device_version(
    session: Session,
    device: Device,
    raw: Mapping[str, object],
    *,
    individual_address: str | None,
    location_id: UUID | None,
    segment_id: UUID | None,
    fallback: datetime,
) -> None:
    title = _optional_str(raw.get("name")) or device.ets_id
    fields = {
        "title": title,
        "description": _optional_str(raw.get("description")),
        "comment": _optional_str(raw.get("comment")),
        "last_downloaded": _last_downloaded(raw.get("last_download")),
        "serial_number": _optional_str(raw.get("serial_number")),
        "individual_address": individual_address,
        "firmware_version": _optional_str(raw.get("firmware_version")),
        "hardware_version": _optional_str(raw.get("hardware_version")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "communication_part_loaded": _loaded_flag(
            raw.get("communication_part_loaded")
        ),
        "individual_address_loaded": _loaded_flag(
            raw.get("individual_address_loaded")
        ),
        "application_program_loaded": _loaded_flag(
            raw.get("application_program_loaded")
        ),
        "parameters_loaded": _loaded_flag(raw.get("parameters_loaded")),
        "medium_config_loaded": _loaded_flag(raw.get("medium_config_loaded")),
        "product_ref": _optional_str(raw.get("product_ref")),
        "hardware_program_ref": _optional_str(raw.get("hardware_program_ref")),
        "application_program_ref": _optional_str(raw.get("application")),
        "bus_current": _optional_int(raw.get("bus_current")),
        "installation_hints": _optional_str(raw.get("installation_hints")),
        "at_type": None,
        "location_id": location_id,
        "segment_id": segment_id,
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    last_modified = fields["last_modified"]
    existing_at_modified = next(
        (item for item in device.versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return
    if device.versions:
        current = max(device.versions, key=lambda item: item.last_modified)
        incoming = tuple(fields[name] for name in DEVICE_SEMANTIC_FIELDS)
        existing = tuple(getattr(current, name) for name in DEVICE_SEMANTIC_FIELDS)
        if incoming == existing:
            return
    version = DeviceVersion(device_id=device.id, **fields)
    session.add(version)
    device.versions.append(version)


def _ia_to_location_id(
    locations_raw: object,
    locations_by_ets: dict[str, Location],
) -> dict[str, UUID]:
    mapping: dict[str, UUID] = {}
    if not isinstance(locations_raw, Mapping):
        return mapping
    for space, ets_id, _parent in _walk_spaces(locations_raw, None):
        location = locations_by_ets.get(ets_id)
        if location is None:
            continue
        devices = space.get("devices")
        if not isinstance(devices, list):
            continue
        for ia in devices:
            if isinstance(ia, str) and ia:
                mapping[ia] = location.id
    return mapping


def _walk_spaces(
    locations: Mapping[str, object],
    parent_ets_id: str | None,
) -> Iterator[tuple[Mapping[str, object], str, str | None]]:
    for space in locations.values():
        if not isinstance(space, Mapping):
            continue
        ets_id = _ets_id(space.get("ets_id"), space.get("identifier"))
        if not ets_id:
            continue
        yield space, ets_id, parent_ets_id
        nested = space.get("spaces")
        if isinstance(nested, Mapping):
            yield from _walk_spaces(nested, ets_id)


def _devices_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Device]:
    rows = session.scalars(
        select(Device)
        .where(Device.installation_id == installation_id)
        .options(selectinload(Device.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _locations_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, Location]:
    rows = session.scalars(
        select(Location).where(Location.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _segments_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Segment]:
    rows = session.scalars(
        select(Segment).where(Segment.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _ets_id(explicit: object, identifier: object) -> str | None:
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


def _loaded_flag(raw: object) -> bool:
    """Map Device *Loaded; missing/None → False (upstream omit)."""
    if isinstance(raw, bool):
        return raw
    return False


def _optional_int(raw: object) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    text = _optional_str(raw)
    if text is None or not text.isdigit():
        return None
    return int(text)


def _completion_status(raw: object) -> str | None:
    value = _optional_str(raw)
    if value is None:
        return None
    if value not in COMPLETION_STATUS_VALUES:
        raise KnxprojImportError(f"unsupported completion status {value!r}")
    return value


def _last_downloaded(raw: object) -> datetime | None:
    text = _optional_str(raw)
    if text is None or text.startswith("0001-01-01"):
        return None
    try:
        parsed = parse_ets_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed is None or parsed.year <= 1:
        return None
    return _aware_utc(parsed)


def _last_modified(raw: object, fallback: datetime) -> datetime:
    text = _optional_str(raw)
    parsed: datetime | None = None
    if text is not None:
        try:
            parsed = parse_ets_datetime(text)
        except (TypeError, ValueError):
            parsed = None
    if parsed is None:
        parsed = fallback
    return _aware_utc(parsed)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
