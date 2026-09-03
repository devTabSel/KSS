from fastapi import APIRouter
from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    datapoint_resource,
    error_response,
    group_range_resource,
    item_document,
    parse_resource_id,
)
from kss.services.datapoints import (
    current_datapoint_pairs,
    current_group_range_pairs,
    get_current_datapoint,
    get_current_group_range,
)

read_router = APIRouter()
kss_router = APIRouter()


def _list_datapoints_response(
    session: Session,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    rows = current_datapoint_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        datapoint_resource(datapoint, version, extra=extra)
        for datapoint, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def _get_datapoint_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(datapoint_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "datapoint not found")
    current = get_current_datapoint(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "datapoint not found")
    datapoint, version = current
    return JSONAPIResponse(
        content=item_document(datapoint_resource(datapoint, version, extra=extra))
    )


@read_router.get("/datapoints")
def list_datapoints(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_datapoints_response(
        session,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/datapoints/{datapoint_id}")
def get_datapoint(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    return _get_datapoint_response(session, datapoint_id, extra=extra)


def _list_group_ranges_response(
    session: Session,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    rows = current_group_range_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        group_range_resource(group_range, version, extra=extra)
        for group_range, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


@kss_router.get("/group-ranges")
def list_group_ranges(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_group_ranges_response(
        session,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/group-ranges/{group_range_id}")
def get_group_range(
    group_range_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(group_range_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "group range not found")
    current = get_current_group_range(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "group range not found")
    group_range, version = current
    return JSONAPIResponse(
        content=item_document(group_range_resource(group_range, version, extra=extra))
    )
