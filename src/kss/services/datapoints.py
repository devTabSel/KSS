"""Upsert GroupRange, Datapoint and FunctionDatapoint from knxproj parse output.

Identity is ``ets_id`` (``GR-n`` / ``GA-n``), never the dict key (display address).
``at_type`` is ``["knx:FunctionPoint"]``. DPT token is ``datapoint_subtype_ets_id``.
Does not persist BUS. Missing entities are not unlinked.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import COMPLETION_STATUS_VALUES
from kss.models.datapoint import Datapoint, DatapointVersion, GroupRange, GroupRangeVersion
from kss.models.installation import Installation
from kss.models.location import Function, FunctionDatapoint
from kss.services.knxproj import KnxprojImportError, parse_ets_datetime

DATAPOINT_AT_TYPE = ["knx:FunctionPoint"]

GROUP_RANGE_SEMANTIC_FIELDS = (
    "name",
    "comment",
    "description",
    "parent_group_range_id",
    "range_start",
    "range_end",
    "unfiltered",
    "completion_status",
    "security",
)

DATAPOINT_SEMANTIC_FIELDS = (
    "name",
    "description",
    "comment",
    "group_address",
    "datapoint_subtype_ets_id",
    "at_type",
    "readable",
    "writable",
    "security",
    "group_range_id",
    "purpose",
    "unfiltered",
    "central",
    "completion_status",
    "global_",
    "key",
)

FUNCTION_DATAPOINT_SEMANTIC_FIELDS = ("ets_id", "role", "linked")


def current_datapoint_pairs(
    session: Session,
) -> list[tuple[Datapoint, DatapointVersion]]:
    datapoints = session.scalars(
        select(Datapoint)
        .options(selectinload(Datapoint.versions))
        .order_by(Datapoint.id)
    ).all()
    rows: list[tuple[Datapoint, DatapointVersion]] = []
    for datapoint in datapoints:
        if not datapoint.versions:
            continue
        current = max(datapoint.versions, key=lambda item: item.last_modified)
        rows.append((datapoint, current))
    return rows


def get_current_datapoint(
    session: Session, datapoint_id: UUID
) -> tuple[Datapoint, DatapointVersion] | None:
    datapoint = session.get(
        Datapoint, datapoint_id, options=(selectinload(Datapoint.versions),)
    )
    if datapoint is None or not datapoint.versions:
        return None
    current = max(datapoint.versions, key=lambda item: item.last_modified)
    return datapoint, current


def current_group_range_pairs(
    session: Session,
) -> list[tuple[GroupRange, GroupRangeVersion]]:
    ranges = session.scalars(
        select(GroupRange)
        .options(selectinload(GroupRange.versions))
        .order_by(GroupRange.id)
    ).all()
    rows: list[tuple[GroupRange, GroupRangeVersion]] = []
    for group_range in ranges:
        if not group_range.versions:
            continue
        current = max(group_range.versions, key=lambda item: item.last_modified)
        rows.append((group_range, current))
    return rows


def get_current_group_range(
    session: Session, group_range_id: UUID
) -> tuple[GroupRange, GroupRangeVersion] | None:
    group_range = session.get(
        GroupRange, group_range_id, options=(selectinload(GroupRange.versions),)
    )
    if group_range is None or not group_range.versions:
        return None
    current = max(group_range.versions, key=lambda item: item.last_modified)
    return group_range, current


def upsert_datapoints_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    fallback = _aware_utc(fallback_last_modified)
    ranges_by_ets = _upsert_group_ranges(
        session, installation, project.get("group_ranges"), fallback
    )
    datapoints_by_ets = _upsert_datapoints(
        session,
        installation,
        project.get("group_addresses"),
        _address_to_range_id(project.get("group_ranges"), ranges_by_ets),
        fallback,
    )
    _upsert_function_datapoints(
        session,
        installation,
        project.get("functions"),
        datapoints_by_ets,
        fallback,
    )


def _upsert_group_ranges(
    session: Session,
    installation: Installation,
    ranges_raw: object,
    fallback: datetime,
) -> dict[str, GroupRange]:
    by_ets = _group_ranges_by_ets_id(session, installation.id)
    if not isinstance(ranges_raw, Mapping):
        return by_ets
    flattened = list(_walk_group_ranges(ranges_raw, None))
    new_identities: list[GroupRange] = []
    for _raw, ets_id, _parent in flattened:
        if ets_id in by_ets:
            continue
        group_range = GroupRange(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(group_range)
        by_ets[ets_id] = group_range
        new_identities.append(group_range)
    if new_identities:
        session.flush()
    for raw, ets_id, parent_ets_id in flattened:
        parent_id = None
        if parent_ets_id and parent_ets_id != ets_id:
            parent = by_ets.get(parent_ets_id)
            if parent is not None:
                parent_id = parent.id
        _upsert_group_range_version(
            session, by_ets[ets_id], raw, parent_id=parent_id, fallback=fallback
        )
    session.flush()
    return by_ets


def _upsert_datapoints(
    session: Session,
    installation: Installation,
    addresses_raw: object,
    address_to_range: dict[str, UUID],
    fallback: datetime,
) -> dict[str, Datapoint]:
    by_ets = _datapoints_by_ets_id(session, installation.id)
    if not isinstance(addresses_raw, Mapping):
        return by_ets
    rows: list[tuple[Mapping[str, object], str, str | None]] = []
    new_identities: list[Datapoint] = []
    for key, raw in addresses_raw.items():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _ets_id(raw.get("ets_id"), raw.get("identifier"))
        if not ets_id:
            continue
        address = key if isinstance(key, str) else _optional_str(raw.get("address"))
        rows.append((raw, ets_id, address))
        if ets_id in by_ets:
            continue
        datapoint = Datapoint(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(datapoint)
        by_ets[ets_id] = datapoint
        new_identities.append(datapoint)
    if new_identities:
        session.flush()
    for raw, ets_id, address in rows:
        group_range_id = address_to_range.get(address) if address else None
        _upsert_datapoint_version(
            session,
            by_ets[ets_id],
            raw,
            group_range_id=group_range_id,
            fallback=fallback,
        )
    session.flush()
    return by_ets


def _upsert_function_datapoints(
    session: Session,
    installation: Installation,
    functions_raw: object,
    datapoints_by_ets: dict[str, Datapoint],
    fallback: datetime,
) -> None:
    if not isinstance(functions_raw, Mapping):
        return
    functions_by_ets = _functions_by_ets_id(session, installation.id)
    existing_edges = _function_datapoints_by_pair(session, installation.id)
    for key, raw in functions_raw.items():
        if not isinstance(raw, Mapping):
            continue
        function_ets_id = _ets_id(raw.get("ets_id"), raw.get("identifier") or key)
        if not function_ets_id:
            continue
        function = functions_by_ets.get(function_ets_id)
        if function is None:
            continue
        refs = raw.get("group_addresses")
        if not isinstance(refs, Mapping):
            continue
        last_modified = _last_modified(raw.get("last_modified"), fallback)
        for ref_key, ref in refs.items():
            if not isinstance(ref, Mapping):
                continue
            ga_ets_id = _ets_id(ref.get("ga_ets_id"), ref.get("ref_id"))
            datapoint = datapoints_by_ets.get(ga_ets_id) if ga_ets_id else None
            if datapoint is None:
                datapoint = _datapoint_by_display_address(
                    datapoints_by_ets, ref, ref_key
                )
            if datapoint is None:
                continue
            fields = {
                "ets_id": _ets_id(ref.get("ets_id"), ref.get("identifier")),
                "role": _optional_str(ref.get("role")),
                "linked": True,
                "last_modified": last_modified,
            }
            pair = (function.id, datapoint.id)
            versions = existing_edges.setdefault(pair, [])
            existing_at = next(
                (item for item in versions if item.last_modified == last_modified),
                None,
            )
            if existing_at is not None:
                continue
            if versions:
                current = max(versions, key=lambda item: item.last_modified)
                incoming = tuple(fields[name] for name in FUNCTION_DATAPOINT_SEMANTIC_FIELDS)
                existing = tuple(
                    getattr(current, name) for name in FUNCTION_DATAPOINT_SEMANTIC_FIELDS
                )
                if incoming == existing:
                    continue
            edge = FunctionDatapoint(
                function_id=function.id,
                datapoint_id=datapoint.id,
                **fields,
            )
            session.add(edge)
            versions.append(edge)
    session.flush()


def _datapoint_by_display_address(
    datapoints_by_ets: dict[str, Datapoint],
    ref: Mapping[str, object],
    ref_key: object,
) -> Datapoint | None:
    display = _optional_str(ref.get("address"))
    if display is None and isinstance(ref_key, str):
        display = ref_key
    raw = _parse_display_group_address(display)
    if raw is None:
        return None
    for item in datapoints_by_ets.values():
        if not item.versions:
            continue
        current = max(item.versions, key=lambda row: row.last_modified)
        if current.group_address == raw:
            return item
    return None


def _upsert_group_range_version(
    session: Session,
    group_range: GroupRange,
    raw: Mapping[str, object],
    *,
    parent_id: UUID | None,
    fallback: datetime,
) -> None:
    fields = {
        "name": _optional_str(raw.get("name")),
        "comment": _optional_str(raw.get("comment")),
        "description": _optional_str(raw.get("description")),
        "parent_group_range_id": parent_id,
        "range_start": _optional_int(raw.get("address_start")),
        "range_end": _optional_int(raw.get("address_end")),
        "unfiltered": _optional_bool(raw.get("unfiltered")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "security": _optional_str(raw.get("security")),
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        versions=group_range.versions,
        version_cls=GroupRangeVersion,
        fk={"group_range_id": group_range.id},
        semantic_fields=GROUP_RANGE_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_datapoint_version(
    session: Session,
    datapoint: Datapoint,
    raw: Mapping[str, object],
    *,
    group_range_id: UUID | None,
    fallback: datetime,
) -> None:
    subtype = _datapoint_subtype(raw.get("datapoint_type_ref"))
    fields = {
        "name": _optional_str(raw.get("name")) or datapoint.ets_id,
        "description": _optional_str(raw.get("description")),
        "comment": _optional_str(raw.get("comment")),
        "group_address": _optional_int(raw.get("raw_address")),
        "datapoint_subtype_ets_id": subtype,
        "at_type": list(DATAPOINT_AT_TYPE),
        "readable": _optional_bool(raw.get("readable")),
        "writable": _optional_bool(raw.get("writable")),
        "security": _optional_str(raw.get("security")),
        "group_range_id": group_range_id,
        "purpose": _optional_str(raw.get("purpose")),
        "unfiltered": _optional_bool(raw.get("unfiltered")),
        "central": _optional_bool(raw.get("central")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "global_": _optional_bool(raw.get("global_")),
        "key": _optional_str(raw.get("key")),
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        versions=datapoint.versions,
        version_cls=DatapointVersion,
        fk={"datapoint_id": datapoint.id},
        semantic_fields=DATAPOINT_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_version(
    session: Session,
    *,
    versions: list[object],
    version_cls: type,
    fk: dict[str, UUID],
    semantic_fields: tuple[str, ...],
    fields: dict[str, object],
) -> None:
    last_modified = fields["last_modified"]
    existing_at_modified = next(
        (item for item in versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return
    if versions:
        current = max(versions, key=lambda item: item.last_modified)
        incoming = tuple(fields[name] for name in semantic_fields)
        existing = tuple(getattr(current, name) for name in semantic_fields)
        if incoming == existing:
            return
    version = version_cls(**fk, **fields)
    session.add(version)
    versions.append(version)


def _walk_group_ranges(
    ranges: Mapping[str, object],
    parent_ets_id: str | None,
) -> Iterator[tuple[Mapping[str, object], str, str | None]]:
    for raw in ranges.values():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _ets_id(raw.get("ets_id"), raw.get("identifier"))
        if not ets_id:
            continue
        yield raw, ets_id, parent_ets_id
        nested = raw.get("group_ranges")
        if isinstance(nested, Mapping):
            yield from _walk_group_ranges(nested, ets_id)


def _address_to_range_id(
    ranges_raw: object, ranges_by_ets: dict[str, GroupRange]
) -> dict[str, UUID]:
    mapping: dict[str, UUID] = {}
    if not isinstance(ranges_raw, Mapping):
        return mapping
    for raw, ets_id, _parent in _walk_group_ranges(ranges_raw, None):
        group_range = ranges_by_ets.get(ets_id)
        if group_range is None:
            continue
        addresses = raw.get("group_addresses")
        if not isinstance(addresses, list):
            continue
        for address in addresses:
            if isinstance(address, str) and address:
                mapping[address] = group_range.id
    return mapping


def _group_ranges_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, GroupRange]:
    rows = session.scalars(
        select(GroupRange)
        .where(GroupRange.installation_id == installation_id)
        .options(selectinload(GroupRange.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _datapoints_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, Datapoint]:
    rows = session.scalars(
        select(Datapoint)
        .where(Datapoint.installation_id == installation_id)
        .options(selectinload(Datapoint.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _functions_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Function]:
    rows = session.scalars(
        select(Function).where(Function.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _function_datapoints_by_pair(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, UUID], list[FunctionDatapoint]]:
    rows = session.scalars(
        select(FunctionDatapoint)
        .join(Function, Function.id == FunctionDatapoint.function_id)
        .where(Function.installation_id == installation_id)
    ).all()
    grouped: dict[tuple[UUID, UUID], list[FunctionDatapoint]] = {}
    for row in rows:
        grouped.setdefault((row.function_id, row.datapoint_id), []).append(row)
    return grouped


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


def _optional_bool(raw: object) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    return None


def _parse_display_group_address(raw: str | None) -> int | None:
    if raw is None:
        return None
    if raw.isdigit():
        value = int(raw)
        return value if 0 <= value <= 65535 else None
    parts = raw.split("/")
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        main, middle, sub = nums
        return (main << 11) | (middle << 8) | sub
    if len(nums) == 2:
        main, sub = nums
        return (main << 11) | sub
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


def _datapoint_subtype(raw: object) -> str | None:
    value = _optional_str(raw)
    if value is None:
        return None
    token = value.split()[0]
    if token.startswith(("DPST-", "DPT-")):
        return token
    return None


def _completion_status(raw: object) -> str | None:
    value = _optional_str(raw)
    if value is None:
        return None
    if value not in COMPLETION_STATUS_VALUES:
        raise KnxprojImportError(f"unsupported completion status {value!r}")
    return value


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
