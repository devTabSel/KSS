from fastapi import APIRouter

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    error_response,
    folder_resource,
    item_document,
    parse_resource_id,
)
from kss.services.device_parts import current_folder_pairs, get_current_folder

kss_router = APIRouter()


@kss_router.get("/folders")
def list_folders(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    rows = current_folder_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [folder_resource(folder, version, extra=extra) for folder, version in page]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


@kss_router.get("/folders/{folder_id}")
def get_folder(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(folder_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "folder not found")
    current = get_current_folder(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "folder not found")
    folder, version = current
    return JSONAPIResponse(
        content=item_document(folder_resource(folder, version, extra=extra))
    )
