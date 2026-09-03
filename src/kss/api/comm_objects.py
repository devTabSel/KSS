from fastapi import APIRouter

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    comm_object_resource,
    error_response,
    item_document,
    parse_resource_id,
)
from kss.services.device_parts import current_comm_object_pairs, get_current_comm_object

kss_router = APIRouter()


@kss_router.get("/comm-objects")
def list_comm_objects(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    rows = current_comm_object_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        comm_object_resource(comm_object, version, extra=extra)
        for comm_object, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


@kss_router.get("/comm-objects/{comm_object_id}")
def get_comm_object(
    comm_object_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(comm_object_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "comm object not found")
    current = get_current_comm_object(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "comm object not found")
    comm_object, version = current
    return JSONAPIResponse(
        content=item_document(comm_object_resource(comm_object, version, extra=extra))
    )
