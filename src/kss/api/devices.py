from fastapi import APIRouter
from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    device_resource,
    error_response,
    item_document,
    parse_resource_id,
)
from kss.services.devices import current_device_pairs, get_current_device

read_router = APIRouter()


def _list_devices_response(
    session: Session,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    rows = current_device_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        device_resource(device, version, extra=extra) for device, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def _get_device_response(
    session: Session,
    device_id: str,
    *,
    extra: bool,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(device_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "device not found")
    current = get_current_device(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "device not found")
    device, version = current
    return JSONAPIResponse(
        content=item_document(device_resource(device, version, extra=extra))
    )


@read_router.get("/devices")
def list_devices(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_devices_response(
        session,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/devices/{device_id}")
def get_device(
    device_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    return _get_device_response(session, device_id, extra=extra)
