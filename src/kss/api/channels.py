from fastapi import APIRouter

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    channel_resource,
    collection_document,
    error_response,
    item_document,
    parse_resource_id,
)
from kss.services.device_parts import current_channel_pairs, get_current_channel

kss_router = APIRouter()


@kss_router.get("/channels")
def list_channels(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    rows = current_channel_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        channel_resource(channel, version, extra=extra) for channel, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


@kss_router.get("/channels/{channel_id}")
def get_channel(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(channel_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "channel not found")
    current = get_current_channel(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "channel not found")
    channel, version = current
    return JSONAPIResponse(
        content=item_document(channel_resource(channel, version, extra=extra))
    )
