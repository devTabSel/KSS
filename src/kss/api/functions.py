from fastapi import APIRouter
from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_document,
    error_response,
    function_resource,
    item_document,
    parse_resource_id,
)
from kss.services.locations import current_function_pairs, get_current_function

read_router = APIRouter()


def _list_functions_response(
    session: Session,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    rows = current_function_pairs(session)
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [
        function_resource(function, version, extra=extra)
        for function, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def _get_function_response(
    session: Session,
    function_id: str,
    *,
    extra: bool,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(function_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "function not found")
    current = get_current_function(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "function not found")
    function, version = current
    return JSONAPIResponse(
        content=item_document(function_resource(function, version, extra=extra))
    )


@read_router.get("/functions")
def list_functions(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_functions_response(
        session,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/functions/{function_id}")
def get_function(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    return _get_function_response(session, function_id, extra=extra)
