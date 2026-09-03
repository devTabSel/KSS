"""Upsert Location + Function from knxproj parse output (same PATCH as Installation).

Identity is ``ets_id`` (``BP-n`` / ``F-n``), never the locations dict key (Name).
Does not persist ``function_group_addresses``, device refs, or a synthetic ``prj:Site``.
``default_line_id`` is filled when a Line with that ``ets_id`` already exists
(same PATCH: Topology first). Missing keys skip writes; missing entities are not unlinked.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import COMPLETION_STATUS_VALUES, LOCATION_TYPE_VALUES
from kss.models.installation import Installation
from kss.models.location import Function, FunctionVersion, Location, LocationVersion
from kss.models.topology import Line
from kss.services.knxproj import KnxprojImportError, parse_ets_datetime
from kss.services.temporal import item_at, pairs_at

LOCATION_SEMANTIC_FIELDS = (
    "title",
    "description",
    "comment",
    "number",
    "location_type",
    "usage",
    "completion_status",
    "at_type",
    "parent_location_id",
    "default_line_id",
)

FUNCTION_SEMANTIC_FIELDS = (
    "title",
    "description",
    "comment",
    "function_type_ets_id",
    "at_type",
    "location_id",
    "completion_status",
)

FUNCTION_AT_TYPE = ["core:ApplicationFunction"]


def current_location_pairs(
    session: Session,
) -> list[tuple[Location, LocationVersion]]:
    locations = session.scalars(
        select(Location)
        .options(selectinload(Location.versions))
        .order_by(Location.id)
    ).all()
    return pairs_at(locations)


def get_current_location(
    session: Session, location_id: UUID
) -> tuple[Location, LocationVersion] | None:
    location = session.get(
        Location, location_id, options=(selectinload(Location.versions),)
    )
    found = item_at(location)
    if found is None:
        return None
    return found[0], found[1]


def current_application_function_pairs(
    session: Session,
) -> list[tuple[Function, FunctionVersion]]:
    functions = session.scalars(
        select(Function)
        .options(selectinload(Function.versions))
        .order_by(Function.id)
    ).all()
    return pairs_at(functions)


def get_current_application_function(
    session: Session, function_id: UUID
) -> tuple[Function, FunctionVersion] | None:
    function = session.get(
        Function, function_id, options=(selectinload(Function.versions),)
    )
    found = item_at(function)
    if found is None:
        return None
    return found[0], found[1]


def current_child_location_pairs(
    session: Session, parent_location_id: UUID
) -> list[tuple[Location, LocationVersion]]:
    return [
        (location, version)
        for location, version in current_location_pairs(session)
        if version.parent_location_id == parent_location_id
    ]


def upsert_locations_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    fallback = _aware_utc(fallback_last_modified)
    by_ets = _locations_by_ets_id(session, installation.id)
    lines_by_ets = _lines_by_ets_id(session, installation.id)
    _upsert_spaces(
        session,
        installation,
        project.get("locations"),
        by_ets,
        lines_by_ets,
        fallback,
    )
    _upsert_functions(
        session,
        installation,
        project.get("functions"),
        by_ets,
        fallback,
    )


def _upsert_spaces(
    session: Session,
    installation: Installation,
    locations_raw: object,
    by_ets: dict[str, Location],
    lines_by_ets: dict[str, Line],
    fallback: datetime,
) -> None:
    if not isinstance(locations_raw, Mapping):
        return

    new_identities: list[Location] = []
    flattened: list[tuple[Mapping[str, object], str, str | None]] = list(
        _walk_spaces(locations_raw, parent_ets_id=None)
    )
    for _space, ets_id, _parent_ets_id in flattened:
        if ets_id in by_ets:
            continue
        location = Location(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(location)
        by_ets[ets_id] = location
        new_identities.append(location)
    if new_identities:
        session.flush()

    for space, ets_id, parent_ets_id in flattened:
        location = by_ets[ets_id]
        parent_location_id = None
        if parent_ets_id and parent_ets_id != ets_id:
            parent = by_ets.get(parent_ets_id)
            if parent is not None:
                parent_location_id = parent.id
        _upsert_location_version(
            session,
            location,
            space,
            parent_location_id=parent_location_id,
            lines_by_ets=lines_by_ets,
            fallback=fallback,
        )
    session.flush()


def _upsert_functions(
    session: Session,
    installation: Installation,
    functions_raw: object,
    by_ets: dict[str, Location],
    fallback: datetime,
) -> None:
    if not isinstance(functions_raw, Mapping):
        return

    existing = _functions_by_ets_id(session, installation.id)
    new_identities: list[Function] = []
    rows: list[tuple[Mapping[str, object], str]] = []
    for key, raw in functions_raw.items():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _ets_id(raw.get("ets_id"), raw.get("identifier") or key)
        if not ets_id:
            continue
        rows.append((raw, ets_id))
        if ets_id in existing:
            continue
        function = Function(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(function)
        existing[ets_id] = function
        new_identities.append(function)
    if new_identities:
        session.flush()

    for raw, ets_id in rows:
        function = existing[ets_id]
        space_ets_id = _ets_id(None, raw.get("space_id"))
        location_id = None
        if space_ets_id:
            host = by_ets.get(space_ets_id)
            if host is not None:
                location_id = host.id
        _upsert_function_version(
            session,
            function,
            raw,
            location_id=location_id,
            fallback=fallback,
        )
    session.flush()


def _upsert_location_version(
    session: Session,
    location: Location,
    space: Mapping[str, object],
    *,
    parent_location_id: UUID | None,
    lines_by_ets: dict[str, Line],
    fallback: datetime,
) -> None:
    location_type = _location_type(space.get("type"))
    title = _optional_str(space.get("name")) or location.ets_id
    default_line_id = None
    line_ets_id = _ets_id(None, space.get("default_line"))
    if line_ets_id:
        line = lines_by_ets.get(line_ets_id)
        if line is not None:
            default_line_id = line.id
    fields = {
        "title": title,
        "description": _optional_str(space.get("description")),
        "comment": _optional_str(space.get("comment")),
        "number": _optional_str(space.get("number")),
        "location_type": location_type,
        "usage": _optional_str(space.get("usage_id")),
        "completion_status": _completion_status(space.get("completion_status")),
        "at_type": [f"loc:{location_type}"] if location_type else None,
        "parent_location_id": parent_location_id,
        "default_line_id": default_line_id,
        "last_modified": _last_modified(space.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        entity=location,
        versions=location.versions,
        version_cls=LocationVersion,
        fk_name="location_id",
        semantic_fields=LOCATION_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_function_version(
    session: Session,
    function: Function,
    raw: Mapping[str, object],
    *,
    location_id: UUID | None,
    fallback: datetime,
) -> None:
    function_type = _optional_str(raw.get("function_type")) or "FT-0"
    title = _optional_str(raw.get("name")) or function.ets_id
    fields = {
        "title": title,
        "description": _optional_str(raw.get("description")),
        "comment": _optional_str(raw.get("comment")),
        "function_type_ets_id": function_type,
        "at_type": list(FUNCTION_AT_TYPE),
        "location_id": location_id,
        "completion_status": _completion_status(raw.get("completion_status")),
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    _upsert_version(
        session,
        entity=function,
        versions=function.versions,
        version_cls=FunctionVersion,
        fk_name="function_id",
        semantic_fields=FUNCTION_SEMANTIC_FIELDS,
        fields=fields,
    )


def _upsert_version(
    session: Session,
    *,
    entity: Location | Function,
    versions: list[object],
    version_cls: type[LocationVersion] | type[FunctionVersion],
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


def _lines_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Line]:
    rows = session.scalars(
        select(Line).where(Line.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _locations_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, Location]:
    rows = session.scalars(
        select(Location)
        .where(Location.installation_id == installation_id)
        .options(selectinload(Location.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _functions_by_ets_id(
    session: Session, installation_id: UUID
) -> dict[str, Function]:
    rows = session.scalars(
        select(Function)
        .where(Function.installation_id == installation_id)
        .options(selectinload(Function.versions))
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


def _location_type(raw: object) -> str | None:
    value = _optional_str(raw)
    if value is None or value not in LOCATION_TYPE_VALUES:
        return None
    return value


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
