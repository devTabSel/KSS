from sqlalchemy.orm import Session

from kss.api.deps import PageNumber, PageSize, SessionDep
from kss.api.flavor import ApiBaseDep, ExtraDep, api_router
from kss.api.jsonapi import (
    JSONAPIResponse,
    channel_resource,
    collection_from_item_dicts,
    collection_from_pairs,
    datapoint_resource,
    empty_related_item,
    error_response,
    folder_resource,
    item_document,
    parse_resource_id,
    serialize_device,
)
from kss.services.device_parts import (
    current_channel_pairs,
    current_child_channel_pairs,
    current_direct_datapoints_for_channel,
    current_folders_for_channel,
    get_current_channel,
)
from kss.services.devices import get_current_device

kss_router = api_router()

_NO_CHANNEL_DEVICE = "The channel is not related to a device."
_NO_PARENT_CHANNEL = "The channel is not related to a parent channel."
_NO_PARENT_DEVICE = "The channel is not a direct child of a device."
_NOT_FOUND = "channel not found"


def _require_channel(session: Session, channel_id: str):
    parsed_id = parse_resource_id(channel_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_channel(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_channels_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_channel_pairs(session),
        channel_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_channel_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    _parsed_id, (channel, version) = required
    return JSONAPIResponse(
        content=item_document(
            channel_resource(channel, version, extra=extra, base=base)
        )
    )


def _get_channel_device_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    _parsed_id, (channel, _version) = required
    related = get_current_device(session, channel.device_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_CHANNEL_DEVICE))
    device, device_version = related
    return JSONAPIResponse(
        content=item_document(
            serialize_device(session, device, device_version, extra=extra, base=base)
        )
    )


def _get_channel_parent_device_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    _parsed_id, (_channel, version) = required
    if version.parent_channel_id is not None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_DEVICE))
    return _get_channel_device_response(
        session, channel_id, extra=extra, base=base
    )


def _get_channel_tree_parent_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    _parsed_id, (_channel, version) = required
    if version.parent_channel_id is not None:
        return _get_channel_parent_response(
            session, channel_id, extra=extra, base=base
        )
    return _get_channel_device_response(
        session, channel_id, extra=extra, base=base
    )


def _get_channel_parent_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    _parsed_id, (_channel, version) = required
    if version.parent_channel_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_CHANNEL))
    related = get_current_channel(session, version.parent_channel_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_CHANNEL))
    parent, parent_version = related
    return JSONAPIResponse(
        content=item_document(
            channel_resource(parent, parent_version, extra=extra, base=base)
        )
    )


def _list_child_channels_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_child_channel_pairs(session, parsed_id),
        channel_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_channel_child_folders_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_folders_for_channel(session, parsed_id),
        folder_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_channel_child_datapoints_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_direct_datapoints_for_channel(session, parsed_id),
        datapoint_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_channel_children_response(
    session: Session,
    channel_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_channel(session, channel_id)
    if error is not None:
        return error
    parsed_id, _current = required
    items = [
        channel_resource(entity, version, extra=extra, base=base)
        for entity, version in current_child_channel_pairs(session, parsed_id)
    ]
    items.extend(
        folder_resource(entity, version, extra=extra, base=base)
        for entity, version in current_folders_for_channel(session, parsed_id)
    )
    items.extend(
        datapoint_resource(entity, version, extra=extra, base=base)
        for entity, version in current_direct_datapoints_for_channel(
            session, parsed_id
        )
    )
    return collection_from_item_dicts(
        items,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/channels")
def list_channels(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_channels_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/channels/{channel_id}")
def get_channel(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_channel_response(session, channel_id, extra=extra, base=base)


@kss_router.get("/channels/{channel_id}/device")
def get_channel_device(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_channel_device_response(
        session, channel_id, extra=extra, base=base
    )


@kss_router.get("/channels/{channel_id}/parentdevice")
def get_channel_parent_device(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_channel_parent_device_response(
        session, channel_id, extra=extra, base=base
    )


@kss_router.get("/channels/{channel_id}/parent")
def get_channel_tree_parent(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_channel_tree_parent_response(
        session, channel_id, extra=extra, base=base
    )


@kss_router.get("/channels/{channel_id}/parentchannel")
def get_channel_parent(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_channel_parent_response(
        session, channel_id, extra=extra, base=base
    )


@kss_router.get("/channels/{channel_id}/childchannels")
def list_child_channels(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_child_channels_response(
        session,
        channel_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/channels/{channel_id}/childfolders")
def list_channel_child_folders(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_channel_child_folders_response(
        session,
        channel_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/channels/{channel_id}/childdatapoints")
def list_channel_child_datapoints(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_channel_child_datapoints_response(
        session,
        channel_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/channels/{channel_id}/children")
def list_channel_children(
    channel_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_channel_children_response(
        session,
        channel_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )
