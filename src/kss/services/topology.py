"""Upsert Area / Line / Segment from knxproj parse output (same PATCH as Installation).

Identity is ``ets_id`` (``A-n`` / ``L-n`` / ``S-n``), never the topology dict key
(area/line address). Missing keys skip writes; missing entities are not unlinked.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import COMPLETION_STATUS_VALUES
from kss.models.installation import Installation
from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.services.knxproj import KnxprojImportError, parse_ets_datetime

AREA_SEMANTIC_FIELDS = (
    "name",
    "address",
    "description",
    "completion_status",
)

LINE_SEMANTIC_FIELDS = (
    "name",
    "address",
    "area_id",
    "medium_type_ets_id",
    "description",
    "completion_status",
)

SEGMENT_SEMANTIC_FIELDS = (
    "name",
    "medium_type_ets_id",
    "line_id",
    "number",
    "description",
    "completion_status",
)


def current_area_pairs(session: Session) -> list[tuple[Area, AreaVersion]]:
    areas = session.scalars(
        select(Area).options(selectinload(Area.versions)).order_by(Area.id)
    ).all()
    rows: list[tuple[Area, AreaVersion]] = []
    for area in areas:
        if not area.versions:
            continue
        current = max(area.versions, key=lambda item: item.last_modified)
        rows.append((area, current))
    return rows


def get_current_area(session: Session, area_id: UUID) -> tuple[Area, AreaVersion] | None:
    area = session.get(Area, area_id, options=(selectinload(Area.versions),))
    if area is None or not area.versions:
        return None
    current = max(area.versions, key=lambda item: item.last_modified)
    return area, current


def current_line_pairs(session: Session) -> list[tuple[Line, LineVersion]]:
    lines = session.scalars(
        select(Line).options(selectinload(Line.versions)).order_by(Line.id)
    ).all()
    rows: list[tuple[Line, LineVersion]] = []
    for line in lines:
        if not line.versions:
            continue
        current = max(line.versions, key=lambda item: item.last_modified)
        rows.append((line, current))
    return rows


def get_current_line(session: Session, line_id: UUID) -> tuple[Line, LineVersion] | None:
    line = session.get(Line, line_id, options=(selectinload(Line.versions),))
    if line is None or not line.versions:
        return None
    current = max(line.versions, key=lambda item: item.last_modified)
    return line, current


def current_segment_pairs(session: Session) -> list[tuple[Segment, SegmentVersion]]:
    segments = session.scalars(
        select(Segment).options(selectinload(Segment.versions)).order_by(Segment.id)
    ).all()
    rows: list[tuple[Segment, SegmentVersion]] = []
    for segment in segments:
        if not segment.versions:
            continue
        current = max(segment.versions, key=lambda item: item.last_modified)
        rows.append((segment, current))
    return rows


def get_current_segment(
    session: Session, segment_id: UUID
) -> tuple[Segment, SegmentVersion] | None:
    segment = session.get(
        Segment, segment_id, options=(selectinload(Segment.versions),)
    )
    if segment is None or not segment.versions:
        return None
    current = max(segment.versions, key=lambda item: item.last_modified)
    return segment, current


def upsert_topology_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    topology_raw = project.get("topology")
    if not isinstance(topology_raw, Mapping):
        return
    fallback = _aware_utc(fallback_last_modified)
    areas_by_ets = _areas_by_ets_id(session, installation.id)
    lines_by_ets = _lines_by_ets_id(session, installation.id)
    segments_by_ets = _segments_by_ets_id(session, installation.id)

    area_rows: list[tuple[Mapping[str, object], str, int]] = []
    line_rows: list[tuple[Mapping[str, object], str, int, str]] = []
    segment_rows: list[tuple[Mapping[str, object], str, str]] = []
    for area_key, area_raw in topology_raw.items():
        if not isinstance(area_raw, Mapping):
            continue
        area_ets_id = _ets_id(area_raw.get("ets_id"), area_raw.get("identifier"))
        if not area_ets_id:
            continue
        area_address = _address(area_raw.get("address"), area_key)
        if area_address is None:
            continue
        area_rows.append((area_raw, area_ets_id, area_address))
        lines_raw = area_raw.get("lines")
        if not isinstance(lines_raw, Mapping):
            continue
        for line_key, line_raw in lines_raw.items():
            if not isinstance(line_raw, Mapping):
                continue
            line_ets_id = _ets_id(line_raw.get("ets_id"), line_raw.get("identifier"))
            if not line_ets_id:
                continue
            line_address = _address(line_raw.get("address"), line_key)
            if line_address is None:
                continue
            line_rows.append((line_raw, line_ets_id, line_address, area_ets_id))
            for segment_raw in _iter_segments(line_raw.get("segments")):
                segment_ets_id = _ets_id(
                    segment_raw.get("ets_id"), segment_raw.get("identifier")
                )
                if not segment_ets_id:
                    continue
                segment_rows.append((segment_raw, segment_ets_id, line_ets_id))

    _create_missing(
        session,
        installation,
        Area,
        areas_by_ets,
        [ets_id for _raw, ets_id, _address in area_rows],
    )
    _create_missing(
        session,
        installation,
        Line,
        lines_by_ets,
        [ets_id for _raw, ets_id, _address, _area in line_rows],
    )
    _create_missing(
        session,
        installation,
        Segment,
        segments_by_ets,
        [ets_id for _raw, ets_id, _line in segment_rows],
    )

    for area_raw, ets_id, address in area_rows:
        _upsert_area_version(
            session,
            areas_by_ets[ets_id],
            area_raw,
            address=address,
            fallback=fallback,
        )
    session.flush()
    for line_raw, ets_id, address, area_ets_id in line_rows:
        area = areas_by_ets.get(area_ets_id)
        if area is None:
            continue
        _upsert_line_version(
            session,
            lines_by_ets[ets_id],
            line_raw,
            address=address,
            area_id=area.id,
            fallback=fallback,
        )
    session.flush()
    for segment_raw, ets_id, line_ets_id in segment_rows:
        line = lines_by_ets.get(line_ets_id)
        if line is None:
            continue
        _upsert_segment_version(
            session,
            segments_by_ets[ets_id],
            segment_raw,
            line_id=line.id,
            fallback=fallback,
        )
    session.flush()


def _create_missing(
    session: Session,
    installation: Installation,
    model: type[Area] | type[Line] | type[Segment],
    by_ets: dict[str, Area] | dict[str, Line] | dict[str, Segment],
    ets_ids: list[str],
) -> None:
    new_identities: list[Area | Line | Segment] = []
    seen: set[str] = set()
    for ets_id in ets_ids:
        if ets_id in seen or ets_id in by_ets:
            continue
        seen.add(ets_id)
        entity = model(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(entity)
        by_ets[ets_id] = entity  # type: ignore[assignment]
        new_identities.append(entity)
    if new_identities:
        session.flush()


def _upsert_area_version(
    session: Session,
    area: Area,
    raw: Mapping[str, object],
    *,
    address: int,
    fallback: datetime,
) -> None:
    fields = {
        "name": _optional_str(raw.get("name")),
        "address": address,
        "description": _optional_str(raw.get("description")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        entity=area,
        versions=area.versions,
        version_cls=AreaVersion,
        fk_name="area_id",
        semantic_fields=AREA_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_line_version(
    session: Session,
    line: Line,
    raw: Mapping[str, object],
    *,
    address: int,
    area_id: UUID,
    fallback: datetime,
) -> None:
    fields = {
        "name": _optional_str(raw.get("name")),
        "address": address,
        "area_id": area_id,
        "medium_type_ets_id": _medium_type_ets_id(
            raw.get("medium_type_ref"), raw.get("medium_type")
        ),
        "description": _optional_str(raw.get("description")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        entity=line,
        versions=line.versions,
        version_cls=LineVersion,
        fk_name="line_id",
        semantic_fields=LINE_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_segment_version(
    session: Session,
    segment: Segment,
    raw: Mapping[str, object],
    *,
    line_id: UUID,
    fallback: datetime,
) -> None:
    fields = {
        "name": _optional_str(raw.get("name")),
        "medium_type_ets_id": _medium_type_ets_id(
            raw.get("medium_type_ref"), raw.get("medium_type")
        ),
        "line_id": line_id,
        "number": _optional_str(raw.get("number")),
        "description": _optional_str(raw.get("description")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        entity=segment,
        versions=segment.versions,
        version_cls=SegmentVersion,
        fk_name="segment_id",
        semantic_fields=SEGMENT_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_version(
    session: Session,
    *,
    entity: Area | Line | Segment,
    versions: list[object],
    version_cls: type[AreaVersion] | type[LineVersion] | type[SegmentVersion],
    fk_name: str,
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
    version = version_cls(**{fk_name: entity.id}, **fields)
    session.add(version)
    versions.append(version)


def _iter_segments(raw: object) -> list[Mapping[str, object]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)]
    if isinstance(raw, Mapping):
        return [item for item in raw.values() if isinstance(item, Mapping)]
    return []


def _areas_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Area]:
    rows = session.scalars(
        select(Area)
        .where(Area.installation_id == installation_id)
        .options(selectinload(Area.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _lines_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Line]:
    rows = session.scalars(
        select(Line)
        .where(Line.installation_id == installation_id)
        .options(selectinload(Line.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _segments_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Segment]:
    rows = session.scalars(
        select(Segment)
        .where(Segment.installation_id == installation_id)
        .options(selectinload(Segment.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _ets_id(explicit: object, identifier: object) -> str | None:
    value = _optional_str(explicit)
    if value:
        return value
    ident = _optional_str(identifier)
    if not ident:
        return None
    return ident.rsplit("_", 1)[-1] or None


def _optional_str(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _medium_type_ets_id(ref: object, fallback: object) -> str | None:
    for candidate in (ref, fallback):
        value = _optional_str(candidate)
        if value and value.startswith("MT-"):
            return value
    return None


def _address(raw: object, key: object) -> int | None:
    for candidate in (raw, key):
        if isinstance(candidate, bool):
            continue
        if isinstance(candidate, int):
            if 0 <= candidate <= 15:
                return candidate
            continue
        text = _optional_str(candidate)
        if text is None or not text.isdigit():
            continue
        value = int(text)
        if 0 <= value <= 15:
            return value
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
