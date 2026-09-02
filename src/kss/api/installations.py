from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, UploadFile
from sqlalchemy.orm import Session
from starlette.responses import Response

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
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
    get_current,
    upsert_installation_from_info,
)
from kss.services.knxproj import KnxprojImportError, parse_knxproj, project_info
from kss.services.master import upsert_master_catalog

read_router = APIRouter()
kss_router = APIRouter()


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
) -> JSONAPIResponse:
    parsed_id = parse_installation_id(installation_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "installation not found")
    current = get_current(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "installation not found")
    installation, version = current
    return JSONAPIResponse(
        content=item_document(
            installation_resource(installation, version, extra=extra)
        )
    )


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


@read_router.get("/installations/{installation_id}")
def get_installation(
    installation_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    return _get_installation_response(session, installation_id, extra=extra)


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
                result = upsert_installation_from_info(
                    session,
                    dict(project_info(project)),
                    import_clock=datetime.now(UTC),
                )
            except KnxprojImportError as exc:
                session.rollback()
                return error_response(422, "Unprocessable Entity", str(exc))
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
            return Response(status_code=201 if result.created else 204)
        case ".ttl":
            return error_response(
                501,
                "Not Implemented",
                "TTL import is not implemented yet; supported now: .knxproj; planned: .ttl",
            )
        case _:
            return error_response(
                422,
                "Unprocessable Entity",
                "unsupported file format; supported now: .knxproj; planned: .ttl",
            )
