from fastapi import APIRouter
from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    error_response,
    item_document,
    location_resource,
    parse_resource_id,
)
from kss.services.locations import current_location_pairs, get_current_location

read_router = APIRouter()


def _list_locations_response(
    session: Session,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    rows = current_location_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        location_resource(location, version, extra=extra)
        for location, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def _get_location_response(
    session: Session,
    location_id: str,
    *,
    extra: bool,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(location_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "location not found")
    current = get_current_location(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "location not found")
    location, version = current
    return JSONAPIResponse(
        content=item_document(location_resource(location, version, extra=extra))
    )


@read_router.get("/locations")
def list_locations(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_locations_response(
        session,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/locations/{location_id}")
def get_location(
    location_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    return _get_location_response(session, location_id, extra=extra)
