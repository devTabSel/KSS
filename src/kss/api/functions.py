from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ApiBaseDep, ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    application_function_resource,
    collection_from_pairs,
    datapoint_resource,
    empty_related_item,
    error_response,
    function_resource,
    group_range_resource,
    item_document,
    location_resource,
    parse_resource_id,
)
from kss.services.datapoints import (
    current_datapoints_for_function,
    current_function_pairs,
    current_functions_for_application_function,
    current_location_for_function,
    get_current_function,
    get_current_group_range,
)
from kss.services.locations import (
    current_application_function_pairs,
    get_current_application_function,
    get_current_location,
)

read_router = api_router()
kss_router = api_router()

_NO_FUNCTION_LOCATION = "The function is not related to a location."
_NO_FUNCTION_GROUP_RANGE = "There is no group range for this function."
_NOT_FOUND = "function not found"
_APPLICATION_FUNCTION_NOT_FOUND = "application function not found"


def _require_function(session: Session, function_id: str):
    parsed_id = parse_resource_id(function_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_function(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_functions_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_function_pairs(session),
        function_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_function_response(
    session: Session,
    function_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_function(session, function_id)
    if error is not None:
        return error
    _parsed_id, (function, version) = required
    return JSONAPIResponse(
        content=item_document(
            function_resource(function, version, extra=extra, base=base)
        )
    )


def _get_function_location_response(
    session: Session,
    function_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_function(session, function_id)
    if error is not None:
        return error
    parsed_id, _current = required
    related = current_location_for_function(session, parsed_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_FUNCTION_LOCATION))
    location, location_version = related
    return JSONAPIResponse(
        content=item_document(
            location_resource(
                location, location_version, extra=extra, base=base
            )
        )
    )


def _list_function_datapoints_response(
    session: Session,
    function_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_function(session, function_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_datapoints_for_function(session, parsed_id),
        datapoint_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_function_group_range_response(
    session: Session,
    function_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_function(session, function_id)
    if error is not None:
        return error
    _parsed_id, (_function, version) = required
    if version.group_range_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_FUNCTION_GROUP_RANGE))
    related = get_current_group_range(session, version.group_range_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_FUNCTION_GROUP_RANGE))
    group_range, group_range_version = related
    return JSONAPIResponse(
        content=item_document(
            group_range_resource(
                group_range, group_range_version, extra=extra, base=base
            )
        )
    )


def _require_application_function(session: Session, function_id: str):
    parsed_id = parse_resource_id(function_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _APPLICATION_FUNCTION_NOT_FOUND)
    current = get_current_application_function(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _APPLICATION_FUNCTION_NOT_FOUND)
    return (parsed_id, current), None


@read_router.get("/functions")
def list_functions(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_functions_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/functions/{function_id}")
def get_function(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_function_response(
        session, function_id, extra=extra, base=base
    )


@read_router.get("/functions/{function_id}/location")
def get_function_location(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_function_location_response(
        session, function_id, extra=extra, base=base
    )


@read_router.get("/functions/{function_id}/datapoints")
def list_function_datapoints(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_function_datapoints_response(
        session,
        function_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/functions/{function_id}/group-range")
def get_function_group_range(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_function_group_range_response(
        session, function_id, extra=extra, base=base
    )


@kss_router.get("/application-functions")
def list_application_functions(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_application_function_pairs(session),
        application_function_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/application-functions/{function_id}")
def get_application_function(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    required, error = _require_application_function(session, function_id)
    if error is not None:
        return error
    _parsed_id, (function, version) = required
    return JSONAPIResponse(
        content=item_document(
            application_function_resource(
                function, version, extra=extra, base=base
            )
        )
    )


@kss_router.get("/application-functions/{function_id}/location")
def get_application_function_location(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    required, error = _require_application_function(session, function_id)
    if error is not None:
        return error
    _parsed_id, (_function, version) = required
    if version.location_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_FUNCTION_LOCATION))
    related = get_current_location(session, version.location_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_FUNCTION_LOCATION))
    location, location_version = related
    return JSONAPIResponse(
        content=item_document(
            location_resource(
                location, location_version, extra=extra, base=base
            )
        )
    )


@kss_router.get("/application-functions/{function_id}/functions")
def list_application_function_functions(
    function_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    required, error = _require_application_function(session, function_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_functions_for_application_function(session, parsed_id),
        function_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )
