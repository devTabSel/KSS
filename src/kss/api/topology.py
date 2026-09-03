from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    area_resource,
    collection_document,
    error_response,
    item_document,
    line_resource,
    parse_resource_id,
    segment_resource,
)
from kss.services.topology import (
    current_area_pairs,
    current_line_pairs,
    current_segment_pairs,
    get_current_area,
    get_current_line,
    get_current_segment,
)

kss_router = api_router()


def _list_response(
    rows: list[tuple[object, object]],
    resource_fn,
    *,
    extra: bool,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    total = len(rows)
    start = page_number * page_size
    page = rows[start : start + page_size]
    items = [resource_fn(entity, version, extra=extra) for entity, version in page]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


@kss_router.get("/areas")
def list_areas(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_response(
        current_area_pairs(session),
        area_resource,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/areas/{area_id}")
def get_area(
    area_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(area_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "area not found")
    current = get_current_area(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "area not found")
    area, version = current
    return JSONAPIResponse(content=item_document(area_resource(area, version, extra=extra)))


@kss_router.get("/lines")
def list_lines(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_response(
        current_line_pairs(session),
        line_resource,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/lines/{line_id}")
def get_line(
    line_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(line_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "line not found")
    current = get_current_line(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "line not found")
    line, version = current
    return JSONAPIResponse(content=item_document(line_resource(line, version, extra=extra)))


@kss_router.get("/segments")
def list_segments(
    session: SessionDep,
    extra: ExtraDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_response(
        current_segment_pairs(session),
        segment_resource,
        extra=extra,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/segments/{segment_id}")
def get_segment(
    segment_id: str,
    session: SessionDep,
    extra: ExtraDep,
) -> JSONAPIResponse:
    parsed_id = parse_resource_id(segment_id)
    if parsed_id is None:
        return error_response(404, "Not Found", "segment not found")
    current = get_current_segment(session, parsed_id)
    if current is None:
        return error_response(404, "Not Found", "segment not found")
    segment, version = current
    return JSONAPIResponse(
        content=item_document(segment_resource(segment, version, extra=extra))
    )
