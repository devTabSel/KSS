"""Read and persist installations (current version = max(last_modified))."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import (
    COMPLETION_STATUS_VALUES,
    GROUP_ADDRESS_STYLE_VALUES,
    PROJECT_TYPE_VALUES,
)
from kss.models.installation import Installation, InstallationVersion
from kss.services.knxproj import KnxprojImportError, parse_ets_datetime
from kss.services.temporal import version_at

MIN_SCHEMA_VERSION = 23
SEMANTIC_FIELDS = (
    "title",
    "comment",
    "contract_number",
    "project_installation_number",
    "completion_status",
    "project_type",
    "master_data_version",
    "schema_version",
    "created_by",
    "tool_version",
    "ip_routing_backbone_key",
    "bcu_key",
    "group_address_style",
)


@dataclass(frozen=True)
class UpsertResult:
    installation: Installation
    version: InstallationVersion
    created: bool
    versioned: bool


def current_pairs(session: Session) -> list[tuple[Installation, InstallationVersion]]:
    installations = session.scalars(
        select(Installation)
        .options(selectinload(Installation.versions))
        .order_by(Installation.id)
    ).all()
    rows: list[tuple[Installation, InstallationVersion]] = []
    for installation in installations:
        if not installation.versions:
            continue
        current = max(installation.versions, key=lambda item: item.last_modified)
        rows.append((installation, current))
    return rows


def get_current(
    session: Session, installation_id: UUID
) -> tuple[Installation, InstallationVersion] | None:
    return get_at(session, installation_id, None)


def get_at(
    session: Session,
    installation_id: UUID,
    at: datetime | None,
) -> tuple[Installation, InstallationVersion] | None:
    installation = session.get(
        Installation, installation_id, options=(selectinload(Installation.versions),)
    )
    if installation is None:
        return None
    current = version_at(installation.versions, at)
    if current is None:
        return None
    return installation, current


def _semantic_values(version: InstallationVersion) -> tuple[object, ...]:
    return tuple(getattr(version, name) for name in SEMANTIC_FIELDS)


def _completion_status(raw: object) -> str:
    status = str(raw) if raw else "Undefined"
    if status not in COMPLETION_STATUS_VALUES:
        raise KnxprojImportError(f"unsupported completion status {status!r}")
    return status


def _group_address_style(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    style = str(raw)
    if style not in GROUP_ADDRESS_STYLE_VALUES:
        raise KnxprojImportError(f"unsupported group address style {style!r}")
    return style


def _schema_version(raw: object) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise KnxprojImportError("schema version missing or invalid") from None


def _optional_str(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _project_start(raw: object) -> datetime | None:
    text = _optional_str(raw)
    if text is not None:
        text = text.strip() or None
    try:
        return parse_ets_datetime(text)
    except (TypeError, ValueError) as exc:
        raise KnxprojImportError("invalid project start") from exc


def _stamp_identity(
    installation: Installation,
    *,
    import_clock: datetime,
    project_start: datetime | None,
) -> None:
    installation.last_import = import_clock
    if project_start is not None:
        installation.project_start = project_start


def _project_type(raw: object) -> str | None:
    value = _optional_str(raw)
    if value is None:
        return None
    if value not in PROJECT_TYPE_VALUES:
        raise KnxprojImportError(f"unsupported project type {value!r}")
    return value


def _conflict_from_integrity(exc: IntegrityError) -> KnxprojImportError:
    detail = str(getattr(exc, "orig", None) or exc)
    if "uq_installations_ets_id" in detail:
        return KnxprojImportError("ets id already exists")
    if "uq_installations_project_guid" in detail:
        return KnxprojImportError("project guid already exists")
    return KnxprojImportError("installation violates a database constraint")


def upsert_installation_from_info(
    session: Session,
    info: dict[str, object],
    *,
    import_clock: datetime,
) -> UpsertResult:
    try:
        return _upsert_installation_from_info(
            session, info, import_clock=import_clock
        )
    except IntegrityError as exc:
        raise _conflict_from_integrity(exc) from exc


def _upsert_installation_from_info(
    session: Session,
    info: dict[str, object],
    *,
    import_clock: datetime,
) -> UpsertResult:
    schema_version = _schema_version(info.get("schema_version"))
    if schema_version < MIN_SCHEMA_VERSION:
        raise KnxprojImportError(
            f"schema version {schema_version} is below {MIN_SCHEMA_VERSION}"
        )

    guid_raw = info.get("guid")
    try:
        project_guid = UUID(str(guid_raw))
    except (TypeError, ValueError) as exc:
        raise KnxprojImportError("project guid missing or invalid") from exc

    title = str(info.get("name") or "")
    comment = _optional_str(info.get("comment"))
    contract_number = _optional_str(info.get("contract_number"))
    project_installation_number = _optional_str(info.get("project_number"))
    completion_status = _completion_status(info.get("completion_status"))
    project_type = _project_type(info.get("project_type"))
    master_data_version_raw = info.get("master_data_version")
    master_data_version = (
        int(master_data_version_raw) if master_data_version_raw is not None else None
    )
    last_modified = parse_ets_datetime(
        str(info["last_modified"]) if info.get("last_modified") else None
    )
    if last_modified is None:
        last_modified = import_clock
    if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=UTC)
    if import_clock.tzinfo is None:
        import_clock = import_clock.replace(tzinfo=UTC)
    project_start = _project_start(info.get("project_start"))

    schema_version_raw = info.get("schema_version")
    schema_version_text = (
        str(schema_version_raw).strip() if schema_version_raw is not None else None
    )
    version_fields = {
        "title": title,
        "comment": comment,
        "contract_number": contract_number,
        "project_installation_number": project_installation_number,
        "completion_status": completion_status,
        "project_type": project_type,
        "master_data_version": master_data_version,
        "schema_version": schema_version_text,
        "created_by": _optional_str(info.get("created_by")),
        "tool_version": _optional_str(info.get("tool_version")),
        "ip_routing_backbone_key": _optional_str(info.get("ip_routing_backbone_key")),
        "bcu_key": _optional_str(info.get("bcu_key")),
        "group_address_style": _group_address_style(info.get("group_address_style")),
        "last_modified": last_modified,
    }

    installation = session.scalars(
        select(Installation)
        .where(Installation.project_guid == project_guid)
        .options(selectinload(Installation.versions))
    ).first()

    if installation is None:
        ets_id = str(info["ets_id"]) if info.get("ets_id") else None
        if not ets_id:
            raise KnxprojImportError("ets id missing")
        installation = Installation(
            id=uuid4(),
            ets_id=ets_id,
            project_guid=project_guid,
            last_import=import_clock,
            project_start=project_start,
        )
        session.add(installation)
        session.flush()
        version = InstallationVersion(
            installation_id=installation.id,
            **version_fields,
        )
        session.add(version)
        session.flush()
        return UpsertResult(
            installation=installation,
            version=version,
            created=True,
            versioned=True,
        )

    _stamp_identity(
        installation,
        import_clock=import_clock,
        project_start=project_start,
    )
    session.flush()

    existing_at_modified = next(
        (item for item in installation.versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return UpsertResult(
            installation=installation,
            version=max(installation.versions, key=lambda item: item.last_modified),
            created=False,
            versioned=False,
        )

    current = max(installation.versions, key=lambda item: item.last_modified)
    incoming_semantics = tuple(version_fields[name] for name in SEMANTIC_FIELDS)
    if incoming_semantics == _semantic_values(current):
        return UpsertResult(
            installation=installation,
            version=current,
            created=False,
            versioned=False,
        )

    version = InstallationVersion(
        installation_id=installation.id,
        **version_fields,
    )
    session.add(version)
    session.flush()
    return UpsertResult(
        installation=installation,
        version=version,
        created=False,
        versioned=True,
    )
