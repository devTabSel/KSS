from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ApiBaseDep, ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_from_pairs,
    device_collection_from_pairs,
    empty_related_item,
    error_response,
    item_document,
    parse_resource_id,
    trade_resource,
)
from kss.services.trades import (
    current_child_trade_pairs,
    current_devices_for_trade,
    current_trade_pairs,
    get_current_trade,
)

kss_router = api_router()

_NO_PARENT_TRADE = "The trade is not related to a parent trade."
_NOT_FOUND = "trade not found"


def _require_trade(session: Session, trade_id: str):
    parsed_id = parse_resource_id(trade_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_trade(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_trades_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_trade_pairs(session),
        trade_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_trade_response(
    session: Session,
    trade_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_trade(session, trade_id)
    if error is not None:
        return error
    _parsed_id, (trade, version) = required
    return JSONAPIResponse(
        content=item_document(
            trade_resource(trade, version, extra=extra, base=base)
        )
    )


def _get_trade_parent_response(
    session: Session,
    trade_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_trade(session, trade_id)
    if error is not None:
        return error
    _parsed_id, (_trade, version) = required
    if version.parent_trade_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_TRADE))
    related = get_current_trade(session, version.parent_trade_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_TRADE))
    parent, parent_version = related
    return JSONAPIResponse(
        content=item_document(
            trade_resource(parent, parent_version, extra=extra, base=base)
        )
    )


def _list_child_trades_response(
    session: Session,
    trade_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_trade(session, trade_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_child_trade_pairs(session, parsed_id),
        trade_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_trade_devices_response(
    session: Session,
    trade_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_trade(session, trade_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return device_collection_from_pairs(
        session,
        current_devices_for_trade(session, parsed_id),
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/trades")
def list_trades(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_trades_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/trades/{trade_id}")
def get_trade(
    trade_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_trade_response(session, trade_id, extra=extra, base=base)


@kss_router.get("/trades/{trade_id}/parenttrade")
def get_trade_parent(
    trade_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_trade_parent_response(session, trade_id, extra=extra, base=base)


@kss_router.get("/trades/{trade_id}/childtrades")
def list_child_trades(
    trade_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_child_trades_response(
        session,
        trade_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/trades/{trade_id}/devices")
def list_trade_devices(
    trade_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_trade_devices_response(
        session,
        trade_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )
