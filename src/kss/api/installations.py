from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import File, Form, Header, Query, UploadFile
from sqlalchemy.orm import Session
from starlette.responses import Response

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    error_response,
    installation_resource,
    item_document,
    parse_installation_id,
)
from kss.services.installations import (
    current_pairs,
    get_at,
    upsert_installation_from_info,
)
from kss.services.knxproj import KnxprojImportError, parse_knxproj, project_info
from kss.services.knxproj_export import (
    KNXPROJ_MEDIA_TYPE,
    TURTLE_MEDIA_TYPE,
    serialize_knxproj,
)
from kss.services.snapshot import snapshot_installation
from kss.services.temporal import lookup_at
from kss.services.ttl_export import serialize_ttl
from kss.services.bus_bindings import upsert_bus_bindings_from_project
from kss.services.datapoints import upsert_datapoints_from_project
from kss.services.device_parts import (
    upsert_comm_object_datapoints_from_project,
    upsert_device_parts_from_project,
)
from kss.services.devices import upsert_devices_from_project
from kss.services.locations import upsert_locations_from_project
from kss.services.manufacturer_catalog import upsert_manufacturer_catalog
from kss.services.master import upsert_master_catalog
from kss.services.topology import upsert_topology_from_project
from kss.services.trades import upsert_trades_from_project
from kss.services.ttl import TtlImportError, ingest_ttl

read_router = api_router()
kss_router = api_router()


def _accept_language(header: str | None) -> str | None:
    """First Accept-Language range without q-weight. Missing or empty → None."""
    if not header:
        return None
    first = header.split(",", 1)[0].strip()
    if not first:
        return None
    tag = first.split(";", 1)[0].strip()
    return tag or None


def _list_installations_response(
    session: Session,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    rows = current_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        installation_resource(installation, version, extra=extra)
        for installation, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def _get_installation_response(
    session: Session,
    installation_id: str,
    *,
    extra: bool,
    export: str | None = None,
    less_info: bool = True,
) -> JSONAPIResponse | Response:
    parsed_id = parse_installation_id(installation_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "installation not found")
    lookup = lookup_at()
    if export is not None:
        if not extra:
            return error_response(
                406,
                "Not Acceptable",
                "file export is only available under /api/kss",
            )
        snap = snapshot_installation(session, parsed_id, lookup)
        if snap is None:
            return error_response(404, "Not Found", "installation not found")
        filename_stem = _export_filename(snap.version.title)
        if export == "ttl":
            body = serialize_ttl(snap).encode("utf-8")
            return Response(
                content=body,
                media_type=TURTLE_MEDIA_TYPE,
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{filename_stem}.ttl"'
                    )
                },
            )
        body = serialize_knxproj(snap, less_info=less_info)
        return Response(
            content=body,
            media_type=KNXPROJ_MEDIA_TYPE,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename_stem}.knxproj"'
                )
            },
        )
    current = get_at(session, parsed_id, lookup)
    if current is None:
        return error_response(404, "Not Found", "installation not found")
    installation, version = current
    return JSONAPIResponse(
        content=item_document(
            installation_resource(installation, version, extra=extra)
        )
    )


def _requested_export(
    accept: str | None, export_format: str | None
) -> str | None | tuple[()]:
    if export_format:
        token = export_format.strip().lower().lstrip(".")
        if token in {"ttl", "turtle"}:
            return "ttl"
        if token in {"knxproj", "zip"}:
            return "knxproj"
        return ()
    if not accept:
        return None
    first = accept.split(",", 1)[0].split(";", 1)[0].strip().lower()
    if first in {TURTLE_MEDIA_TYPE, "text/ttl"}:
        return "ttl"
    if first in {KNXPROJ_MEDIA_TYPE, "application/zip", "application/x-knxproj"}:
        return "knxproj"
    return None


def _export_filename(title: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in "-_." else "_" for char in title
    ).strip("._")
    return cleaned or "installation"


@read_router.get("/installations")
def list_installations(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_installations_response(
        session,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/installations/{installation_id}", response_model=None)
def get_installation(
    installation_id: str,
    session: SessionDep,
    extra: ExtraDep,
    less_info: Annotated[bool, Query()] = True,
    export_format: Annotated[str | None, Query(alias="format")] = None,
    accept: Annotated[str | None, Header()] = None,
) -> JSONAPIResponse | Response:
    export = _requested_export(accept, export_format)
    if export == ():
        return error_response(
            422,
            "Unprocessable Entity",
            "unsupported file format; supported now: .knxproj, .ttl",
        )
    return _get_installation_response(
        session,
        installation_id,
        extra=extra,
        export=export,
        less_info=less_info,
    )


@kss_router.patch("/installations", response_model=None)
def patch_installations(
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    filename: Annotated[str | None, Form()] = None,
    created: Annotated[str | None, Form()] = None,
    password: Annotated[str | None, Form()] = None,
    accept_language: Annotated[str | None, Header()] = None,
) -> JSONAPIResponse | Response:
    del created  # file date is not persisted on Installation
    language = _accept_language(accept_language)
    original_name = filename or file.filename or ""
    suffix = Path(original_name).suffix.lower()
    match suffix:
        case ".knxproj":
            tmp_path: Path | None = None
            try:
                with NamedTemporaryFile(suffix=".knxproj", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    while chunk := file.file.read(1024 * 1024):
                        tmp.write(chunk)
                project = parse_knxproj(
                    tmp_path, password=password, language=language
                )
                upsert_master_catalog(session, project.get("master_data"))
                upsert_manufacturer_catalog(
                    session, project.get("manufacturer_data")
                )
                result = upsert_installation_from_info(
                    session,
                    dict(project_info(project)),
                    import_clock=datetime.now(UTC),
                )
                upsert_topology_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_locations_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_devices_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_device_parts_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_datapoints_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_comm_object_datapoints_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_bus_bindings_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
                upsert_trades_from_project(
                    session,
                    result.installation,
                    project,
                    fallback_last_modified=result.version.last_modified,
                )
            except KnxprojImportError as exc:
                session.rollback()
                return error_response(422, "Unprocessable Entity", str(exc))
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
            return Response(status_code=201 if result.created else 204)
        case ".ttl":
            # password and Accept-Language are knxproj-only (no knx_master overlay).
            tmp_path = None
            try:
                with NamedTemporaryFile(suffix=".ttl", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    while chunk := file.file.read(1024 * 1024):
                        tmp.write(chunk)
                result = ingest_ttl(
                    session, tmp_path, import_clock=datetime.now(UTC)
                )
            except TtlImportError as exc:
                session.rollback()
                return error_response(422, "Unprocessable Entity", str(exc))
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
            return Response(status_code=201 if result.created else 204)
        case _:
            return error_response(
                422,
                "Unprocessable Entity",
                "unsupported file format; supported now: .knxproj, .ttl",
            )
