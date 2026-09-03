from fastapi import APIRouter

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    error_response,
    item_document,
    parse_resource_id,
    trade_resource,
)
from kss.services.trades import current_trade_pairs, get_current_trade

kss_router = APIRouter()


@kss_router.get("/trades")
def list_trades(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    rows = current_trade_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [trade_resource(trade, version, extra=extra) for trade, version in page]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


@kss_router.get("/trades/{trade_id}")
def get_trade(
    trade_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(trade_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "trade not found")
    current = get_current_trade(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "trade not found")
    trade, version = current
    return JSONAPIResponse(
        content=item_document(trade_resource(trade, version, extra=extra))
    )
