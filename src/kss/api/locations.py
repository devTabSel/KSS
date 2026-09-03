from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ApiBaseDep, ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_from_pairs,
    device_collection_from_pairs,
    empty_related_item,
    error_response,
    function_resource,
    item_document,
    location_resource,
    parse_resource_id,
)
from kss.services.datapoints import current_functions_for_location
from kss.services.devices import current_devices_for_location
from kss.services.locations import (
    current_child_location_pairs,
    current_location_pairs,
    get_current_location,
)

read_router = api_router()

_NO_PARENT_LOCATION = "The location has no parent location."
_NOT_FOUND = "location not found"


def _require_location(
    session: Session, location_id: str
):
    parsed_id = parse_resource_id(location_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_location(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_locations_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_location_pairs(session),
        location_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_location_response(
    session: Session,
    location_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_location(session, location_id)
    if error is not None:
        return error
    _parsed_id, (location, version) = required
    return JSONAPIResponse(
        content=item_document(
            location_resource(location, version, extra=extra, base=base)
        )
    )


def _get_parent_location_response(
    session: Session,
    location_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_location(session, location_id)
    if error is not None:
        return error
    _parsed_id, (_location, version) = required
    if version.parent_location_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_LOCATION))
    related = get_current_location(session, version.parent_location_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_LOCATION))
    parent, parent_version = related
    return JSONAPIResponse(
        content=item_document(
            location_resource(parent, parent_version, extra=extra, base=base)
        )
    )


def _list_child_locations_response(
    session: Session,
    location_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_location(session, location_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_child_location_pairs(session, parsed_id),
        location_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_location_functions_response(
    session: Session,
    location_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_location(session, location_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_functions_for_location(session, parsed_id),
        function_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_location_devices_response(
    session: Session,
    location_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_location(session, location_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return device_collection_from_pairs(
        session,
        current_devices_for_location(session, parsed_id),
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/locations")
def list_locations(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_locations_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/locations/{location_id}")
def get_location(
    location_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_location_response(
        session, location_id, extra=extra, base=base
    )


@read_router.get("/locations/{location_id}/parentlocation")
def get_parent_location(
    location_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_parent_location_response(
        session, location_id, extra=extra, base=base
    )


@read_router.get("/locations/{location_id}/childlocations")
def list_child_locations(
    location_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_child_locations_response(
        session,
        location_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/locations/{location_id}/functions")
def list_location_functions(
    location_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_location_functions_response(
        session,
        location_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/locations/{location_id}/devices")
def list_location_devices(
    location_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_location_devices_response(
        session,
        location_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )
