from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ApiBaseDep, ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    collection_from_pairs,
    datapoint_resource,
    device_collection_from_pairs,
    empty_related_item,
    error_response,
    item_document,
    location_resource,
    parse_resource_id,
    serialize_device,
)
from kss.services.datapoints import current_datapoints_for_device
from kss.services.devices import current_device_pairs, get_current_device
from kss.services.locations import get_current_location

read_router = api_router()

_NO_DEVICE_LOCATION = "The device is not assigned to a location."
_NOT_FOUND = "device not found"


def _require_device(session: Session, device_id: str):
    parsed_id = parse_resource_id(device_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_device(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_devices_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return device_collection_from_pairs(
        session,
        current_device_pairs(session),
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_device_response(
    session: Session,
    device_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_device(session, device_id)
    if error is not None:
        return error
    _parsed_id, (device, version) = required
    return JSONAPIResponse(
        content=item_document(
            serialize_device(session, device, version, extra=extra, base=base)
        )
    )


def _get_device_location_response(
    session: Session,
    device_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_device(session, device_id)
    if error is not None:
        return error
    _parsed_id, (_device, version) = required
    if version.location_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DEVICE_LOCATION))
    related = get_current_location(session, version.location_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DEVICE_LOCATION))
    location, location_version = related
    return JSONAPIResponse(
        content=item_document(
            location_resource(location, location_version, extra=extra, base=base)
        )
    )


def _list_device_datapoints_response(
    session: Session,
    device_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_device(session, device_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_datapoints_for_device(session, parsed_id),
        datapoint_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/devices")
def list_devices(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_devices_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/devices/{device_id}")
def get_device(
    device_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_device_response(session, device_id, extra=extra, base=base)


@read_router.get("/devices/{device_id}/location")
def get_device_location(
    device_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_device_location_response(
        session, device_id, extra=extra, base=base
    )


@read_router.get("/devices/{device_id}/datapoints")
def list_device_datapoints(
    device_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_device_datapoints_response(
        session,
        device_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )
