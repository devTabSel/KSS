"""Upsert Channel, Folder, CommObject and CO↔GA from knxproj Device extras.

Identity is ``(device_id, ets_id)``. ChannelInstance ``ets_id`` is already
stripped (``DI-n_CI-n``); GOT-only channels keep Node ``@RefId``. Do not
``rsplit``. Missing entities are not unlinked. ``comm_object_datapoints``
needs Datapoint rows and runs after Datapoint upsert.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.datapoint import Datapoint
from kss.models.device import (
    CommObject,
    CommObjectDatapoint,
    CommObjectVersion,
    Device,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceFolder,
    DeviceFolderVersion,
)
from kss.models.installation import Installation
from kss.services.knxproj import parse_ets_datetime

CHANNEL_SEMANTIC_FIELDS = (
    "title",
    "description",
    "catalog_ref",
    "parent_channel_id",
)

FOLDER_SEMANTIC_FIELDS = (
    "title",
    "parent_folder_id",
    "parent_channel_id",
)

COMM_OBJECT_SEMANTIC_FIELDS = (
    "number",
    "name",
    "text",
    "datapoint_subtype_ets_id",
    "communication_flag",
    "read_flag",
    "write_flag",
    "transmit_flag",
    "update_flag",
    "read_on_init_flag",
    "priority",
    "channel_id",
    "folder_id",
)

COMM_OBJECT_DATAPOINT_SEMANTIC_FIELDS = ("linked",)


def current_channel_pairs(
    session: Session,
) -> list[tuple[DeviceChannel, DeviceChannelVersion]]:
    rows = session.scalars(
        select(DeviceChannel)
        .options(selectinload(DeviceChannel.versions))
        .order_by(DeviceChannel.id)
    ).all()
    return _current_pairs(rows)


def get_current_channel(
    session: Session, channel_id: UUID
) -> tuple[DeviceChannel, DeviceChannelVersion] | None:
    channel = session.get(
        DeviceChannel, channel_id, options=(selectinload(DeviceChannel.versions),)
    )
    if channel is None or not channel.versions:
        return None
    current = max(channel.versions, key=lambda item: item.last_modified)
    return channel, current


def current_folder_pairs(
    session: Session,
) -> list[tuple[DeviceFolder, DeviceFolderVersion]]:
    rows = session.scalars(
        select(DeviceFolder)
        .options(selectinload(DeviceFolder.versions))
        .order_by(DeviceFolder.id)
    ).all()
    return _current_pairs(rows)


def get_current_folder(
    session: Session, folder_id: UUID
) -> tuple[DeviceFolder, DeviceFolderVersion] | None:
    folder = session.get(
        DeviceFolder, folder_id, options=(selectinload(DeviceFolder.versions),)
    )
    if folder is None or not folder.versions:
        return None
    current = max(folder.versions, key=lambda item: item.last_modified)
    return folder, current


def current_comm_object_pairs(
    session: Session,
) -> list[tuple[CommObject, CommObjectVersion]]:
    rows = session.scalars(
        select(CommObject)
        .options(selectinload(CommObject.versions))
        .order_by(CommObject.id)
    ).all()
    return _current_pairs(rows)


def get_current_comm_object(
    session: Session, comm_object_id: UUID
) -> tuple[CommObject, CommObjectVersion] | None:
    comm_object = session.get(
        CommObject, comm_object_id, options=(selectinload(CommObject.versions),)
    )
    if comm_object is None or not comm_object.versions:
        return None
    current = max(comm_object.versions, key=lambda item: item.last_modified)
    return comm_object, current


def upsert_device_parts_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    devices_raw = project.get("devices")
    if not isinstance(devices_raw, Mapping):
        return
    fallback = _aware_utc(fallback_last_modified)
    devices_by_ets = _devices_by_ets_id(session, installation.id)
    work = _collect_device_parts(devices_raw, devices_by_ets, fallback)
    if not work:
        return
    channels_by_key = _upsert_channels(session, installation, work)
    _upsert_folders(session, installation, work, channels_by_key)
    _upsert_comm_objects(session, installation, work, channels_by_key)


def upsert_comm_object_datapoints_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    devices_raw = project.get("devices")
    if not isinstance(devices_raw, Mapping):
        return
    fallback = _aware_utc(fallback_last_modified)
    devices_by_ets = _devices_by_ets_id(session, installation.id)
    comm_objects_by_key = _comm_objects_by_device_ets(session, installation.id)
    datapoints_by_ets = _datapoints_by_ets_id(session, installation.id)
    existing_edges = _comm_object_datapoints_by_pair(session, installation.id)
    for raw, device, last_modified in _iter_device_rows(
        devices_raw, devices_by_ets, fallback
    ):
        comm_objects = raw.get("comm_objects")
        if not isinstance(comm_objects, Mapping):
            continue
        for co_raw in comm_objects.values():
            if not isinstance(co_raw, Mapping):
                continue
            co_ets_id = _part_ets_id(co_raw.get("ets_id"))
            if not co_ets_id:
                continue
            comm_object = comm_objects_by_key.get((device.id, co_ets_id))
            if comm_object is None:
                continue
            refs = co_raw.get("group_address_ets_ids")
            if not isinstance(refs, list):
                continue
            for ref in refs:
                ga_ets_id = _part_ets_id(ref)
                if not ga_ets_id:
                    continue
                datapoint = datapoints_by_ets.get(ga_ets_id)
                if datapoint is None:
                    continue
                fields = {"linked": True, "last_modified": last_modified}
                pair = (comm_object.id, datapoint.id)
                versions = existing_edges.setdefault(pair, [])
                if _skip_version(versions, fields, COMM_OBJECT_DATAPOINT_SEMANTIC_FIELDS):
                    continue
                edge = CommObjectDatapoint(
                    comm_object_id=comm_object.id,
                    datapoint_id=datapoint.id,
                    **fields,
                )
                session.add(edge)
                versions.append(edge)
    session.flush()


def _collect_device_parts(
    devices_raw: Mapping[str, object],
    devices_by_ets: dict[str, Device],
    fallback: datetime,
) -> list[tuple[Mapping[str, object], Device, datetime]]:
    work: list[tuple[Mapping[str, object], Device, datetime]] = []
    for raw, device, last_modified in _iter_device_rows(
        devices_raw, devices_by_ets, fallback
    ):
        tree = raw.get("group_object_tree")
        comm_objects = raw.get("comm_objects")
        has_tree = isinstance(tree, Mapping) and (
            isinstance(tree.get("channels"), Mapping)
            or isinstance(tree.get("folders"), Mapping)
        )
        has_cos = isinstance(comm_objects, Mapping) and bool(comm_objects)
        if has_tree or has_cos:
            work.append((raw, device, last_modified))
    return work


def _iter_device_rows(
    devices_raw: Mapping[str, object],
    devices_by_ets: dict[str, Device],
    fallback: datetime,
) -> list[tuple[Mapping[str, object], Device, datetime]]:
    rows: list[tuple[Mapping[str, object], Device, datetime]] = []
    for raw in devices_raw.values():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _device_ets_id(raw.get("ets_id"), raw.get("identifier"))
        if not ets_id:
            continue
        device = devices_by_ets.get(ets_id)
        if device is None:
            continue
        rows.append((raw, device, _last_modified(raw.get("last_modified"), fallback)))
    return rows


def _upsert_channels(
    session: Session,
    installation: Installation,
    work: list[tuple[Mapping[str, object], Device, datetime]],
) -> dict[tuple[UUID, str], DeviceChannel]:
    by_key = _channels_by_device_ets(session, installation.id)
    new_identities: list[DeviceChannel] = []
    pending: list[tuple[Mapping[str, object], DeviceChannel, datetime]] = []
    for raw, device, last_modified in work:
        tree = raw.get("group_object_tree")
        if not isinstance(tree, Mapping):
            continue
        channels_raw = tree.get("channels")
        if not isinstance(channels_raw, Mapping):
            continue
        for channel_raw in channels_raw.values():
            if not isinstance(channel_raw, Mapping):
                continue
            ets_id = _part_ets_id(channel_raw.get("ets_id"))
            if not ets_id:
                continue
            key = (device.id, ets_id)
            channel = by_key.get(key)
            if channel is None:
                channel = DeviceChannel(
                    id=uuid4(),
                    device_id=device.id,
                    ets_id=ets_id,
                )
                session.add(channel)
                by_key[key] = channel
                new_identities.append(channel)
            pending.append((channel_raw, channel, last_modified))
    if new_identities:
        session.flush()
    for channel_raw, channel, last_modified in pending:
        parent_id = None
        parent_ets_id = _part_ets_id(channel_raw.get("parent_channel_ets_id"))
        if parent_ets_id and parent_ets_id != channel.ets_id:
            parent = by_key.get((channel.device_id, parent_ets_id))
            if parent is not None:
                parent_id = parent.id
        fields = {
            "title": _optional_str(channel_raw.get("title")),
            "description": _optional_str(channel_raw.get("description")),
            "catalog_ref": _optional_str(channel_raw.get("catalog_ref")),
            "parent_channel_id": parent_id,
            "last_modified": last_modified,
        }
        if _skip_version(channel.versions, fields, CHANNEL_SEMANTIC_FIELDS):
            continue
        version = DeviceChannelVersion(channel_id=channel.id, **fields)
        session.add(version)
        channel.versions.append(version)
    session.flush()
    return by_key


def _upsert_folders(
    session: Session,
    installation: Installation,
    work: list[tuple[Mapping[str, object], Device, datetime]],
    channels_by_key: dict[tuple[UUID, str], DeviceChannel],
) -> dict[tuple[UUID, str], DeviceFolder]:
    by_key = _folders_by_device_ets(session, installation.id)
    new_identities: list[DeviceFolder] = []
    pending: list[tuple[Mapping[str, object], DeviceFolder, datetime]] = []
    for raw, device, last_modified in work:
        tree = raw.get("group_object_tree")
        if not isinstance(tree, Mapping):
            continue
        folders_raw = tree.get("folders")
        if not isinstance(folders_raw, Mapping):
            continue
        for folder_raw in folders_raw.values():
            if not isinstance(folder_raw, Mapping):
                continue
            ets_id = _part_ets_id(folder_raw.get("ets_id"))
            if not ets_id:
                continue
            key = (device.id, ets_id)
            folder = by_key.get(key)
            if folder is None:
                folder = DeviceFolder(
                    id=uuid4(),
                    device_id=device.id,
                    ets_id=ets_id,
                )
                session.add(folder)
                by_key[key] = folder
                new_identities.append(folder)
            pending.append((folder_raw, folder, last_modified))
    if new_identities:
        session.flush()
    for folder_raw, folder, last_modified in pending:
        parent_folder_id = None
        parent_channel_id = None
        parent_folder_ets_id = _part_ets_id(folder_raw.get("parent_folder_ets_id"))
        parent_channel_ets_id = _part_ets_id(folder_raw.get("parent_channel_ets_id"))
        if parent_folder_ets_id and parent_folder_ets_id != folder.ets_id:
            parent = by_key.get((folder.device_id, parent_folder_ets_id))
            if parent is not None:
                parent_folder_id = parent.id
        elif parent_channel_ets_id:
            parent_channel = channels_by_key.get(
                (folder.device_id, parent_channel_ets_id)
            )
            if parent_channel is not None:
                parent_channel_id = parent_channel.id
        fields = {
            "title": _optional_str(folder_raw.get("title")),
            "parent_folder_id": parent_folder_id,
            "parent_channel_id": parent_channel_id,
            "last_modified": last_modified,
        }
        if _skip_version(folder.versions, fields, FOLDER_SEMANTIC_FIELDS):
            continue
        version = DeviceFolderVersion(folder_id=folder.id, **fields)
        session.add(version)
        folder.versions.append(version)
    session.flush()
    return by_key


def _upsert_comm_objects(
    session: Session,
    installation: Installation,
    work: list[tuple[Mapping[str, object], Device, datetime]],
    channels_by_key: dict[tuple[UUID, str], DeviceChannel],
) -> None:
    folders_by_key = _folders_by_device_ets(session, installation.id)
    by_key = _comm_objects_by_device_ets(session, installation.id)
    new_identities: list[CommObject] = []
    pending: list[tuple[Mapping[str, object], CommObject, datetime]] = []
    for raw, device, last_modified in work:
        comm_objects = raw.get("comm_objects")
        if not isinstance(comm_objects, Mapping):
            continue
        for co_raw in comm_objects.values():
            if not isinstance(co_raw, Mapping):
                continue
            ets_id = _part_ets_id(co_raw.get("ets_id"))
            if not ets_id:
                continue
            key = (device.id, ets_id)
            comm_object = by_key.get(key)
            if comm_object is None:
                comm_object = CommObject(
                    id=uuid4(),
                    device_id=device.id,
                    ets_id=ets_id,
                )
                session.add(comm_object)
                by_key[key] = comm_object
                new_identities.append(comm_object)
            pending.append((co_raw, comm_object, last_modified))
    if new_identities:
        session.flush()
    for co_raw, comm_object, last_modified in pending:
        channel_id = None
        folder_id = None
        channel_ets_id = _part_ets_id(co_raw.get("channel_ets_id"))
        folder_ets_id = _part_ets_id(co_raw.get("folder_ets_id"))
        if channel_ets_id:
            channel = channels_by_key.get((comm_object.device_id, channel_ets_id))
            if channel is not None:
                channel_id = channel.id
        if folder_ets_id:
            folder = folders_by_key.get((comm_object.device_id, folder_ets_id))
            if folder is not None:
                folder_id = folder.id
        fields = {
            "number": _optional_int(co_raw.get("number")),
            "name": _optional_str(co_raw.get("name")),
            "text": _optional_str(co_raw.get("text")),
            "datapoint_subtype_ets_id": _optional_str(
                co_raw.get("datapoint_subtype_ets_id")
            ),
            "communication_flag": _optional_bool(co_raw.get("communication_flag")),
            "read_flag": _optional_bool(co_raw.get("read_flag")),
            "write_flag": _optional_bool(co_raw.get("write_flag")),
            "transmit_flag": _optional_bool(co_raw.get("transmit_flag")),
            "update_flag": _optional_bool(co_raw.get("update_flag")),
            "read_on_init_flag": _optional_bool(co_raw.get("read_on_init_flag")),
            "priority": _optional_str(co_raw.get("priority")),
            "channel_id": channel_id,
            "folder_id": folder_id,
            "last_modified": last_modified,
        }
        if _skip_version(comm_object.versions, fields, COMM_OBJECT_SEMANTIC_FIELDS):
            continue
        version = CommObjectVersion(comm_object_id=comm_object.id, **fields)
        session.add(version)
        comm_object.versions.append(version)
    session.flush()


def _current_pairs(rows: list) -> list[tuple[object, object]]:
    pairs: list[tuple[object, object]] = []
    for row in rows:
        if not row.versions:
            continue
        current = max(row.versions, key=lambda item: item.last_modified)
        pairs.append((row, current))
    return pairs


def _skip_version(
    versions: list,
    fields: Mapping[str, object],
    semantic_fields: tuple[str, ...],
) -> bool:
    last_modified = fields["last_modified"]
    existing_at_modified = next(
        (item for item in versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return True
    if versions:
        current = max(versions, key=lambda item: item.last_modified)
        incoming = tuple(fields[name] for name in semantic_fields)
        existing = tuple(getattr(current, name) for name in semantic_fields)
        if incoming == existing:
            return True
    return False


def _devices_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Device]:
    rows = session.scalars(
        select(Device).where(Device.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _channels_by_device_ets(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, str], DeviceChannel]:
    rows = session.scalars(
        select(DeviceChannel)
        .join(Device, Device.id == DeviceChannel.device_id)
        .where(Device.installation_id == installation_id)
        .options(selectinload(DeviceChannel.versions))
    ).all()
    return {(row.device_id, row.ets_id): row for row in rows}


def _folders_by_device_ets(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, str], DeviceFolder]:
    rows = session.scalars(
        select(DeviceFolder)
        .join(Device, Device.id == DeviceFolder.device_id)
        .where(Device.installation_id == installation_id)
        .options(selectinload(DeviceFolder.versions))
    ).all()
    return {(row.device_id, row.ets_id): row for row in rows}


def _comm_objects_by_device_ets(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, str], CommObject]:
    rows = session.scalars(
        select(CommObject)
        .join(Device, Device.id == CommObject.device_id)
        .where(Device.installation_id == installation_id)
        .options(selectinload(CommObject.versions))
    ).all()
    return {(row.device_id, row.ets_id): row for row in rows}


def _datapoints_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, Datapoint]:
    rows = session.scalars(
        select(Datapoint).where(Datapoint.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _comm_object_datapoints_by_pair(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, UUID], list[CommObjectDatapoint]]:
    rows = session.scalars(
        select(CommObjectDatapoint)
        .join(CommObject, CommObject.id == CommObjectDatapoint.comm_object_id)
        .join(Device, Device.id == CommObject.device_id)
        .where(Device.installation_id == installation_id)
    ).all()
    grouped: dict[tuple[UUID, UUID], list[CommObjectDatapoint]] = {}
    for row in rows:
        grouped.setdefault((row.comm_object_id, row.datapoint_id), []).append(row)
    return grouped


def _device_ets_id(explicit: object, identifier: object) -> str | None:
    value = _optional_str(explicit)
    if value:
        return value.rsplit("_", 1)[-1] or None
    ident = _optional_str(identifier)
    if not ident:
        return None
    return ident.rsplit("_", 1)[-1] or None


def _part_ets_id(raw: object) -> str | None:
    return _optional_str(raw)


def _optional_str(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _optional_bool(raw: object) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    return None


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
