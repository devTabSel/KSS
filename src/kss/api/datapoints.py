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
    function_resource,
    group_range_resource,
    item_document,
    parse_resource_id,
    serialize_device,
)
from kss.services.datapoints import (
    current_child_group_range_pairs,
    current_datapoint_pairs,
    current_device_for_datapoint,
    current_functions_for_datapoint,
    current_group_range_pairs,
    get_current_datapoint,
    get_current_group_range,
)
from kss.services.device_parts import get_current_channel, get_current_folder

read_router = api_router()
kss_router = api_router()

_NO_DATAPOINT_DEVICE = (
    "There is no device for this datapoint, this type of datapoint does not "
    "support such an assignment."
)
_NO_DATAPOINT_CHANNEL = "The datapoint is not related to a channel."
_NO_DATAPOINT_FOLDER = "The datapoint is not related to a folder."
_NO_PARENT_DEVICE = (
    "The datapoint is not a direct child of a device."
)
_NO_TREE_PARENT = "The datapoint has no tree parent."
_NO_PARENT_GROUP_RANGE = (
    "The group range is not related to a parent group range."
)
_NOT_FOUND = "datapoint not found"
_GROUP_RANGE_NOT_FOUND = "group range not found"


def _require_datapoint(session: Session, datapoint_id: str):
    parsed_id = parse_resource_id(datapoint_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_datapoint(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_datapoints_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_datapoint_pairs(session),
        datapoint_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_datapoint_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    _parsed_id, (datapoint, version) = required
    return JSONAPIResponse(
        content=item_document(
            datapoint_resource(datapoint, version, extra=extra, base=base)
        )
    )


def _list_datapoint_functions_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_functions_for_datapoint(session, parsed_id),
        function_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_datapoint_device_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    parsed_id, _current = required
    related = current_device_for_datapoint(session, parsed_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DATAPOINT_DEVICE))
    device, version = related
    return JSONAPIResponse(
        content=item_document(
            serialize_device(session, device, version, extra=extra, base=base)
        )
    )


def _get_datapoint_channel_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    _parsed_id, (_datapoint, version) = required
    if version.channel_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DATAPOINT_CHANNEL))
    related = get_current_channel(session, version.channel_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DATAPOINT_CHANNEL))
    channel, channel_version = related
    return JSONAPIResponse(
        content=item_document(
            channel_resource(channel, channel_version, extra=extra, base=base)
        )
    )


def _get_datapoint_folder_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    _parsed_id, (_datapoint, version) = required
    if version.folder_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DATAPOINT_FOLDER))
    related = get_current_folder(session, version.folder_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_DATAPOINT_FOLDER))
    folder, folder_version = related
    return JSONAPIResponse(
        content=item_document(
            folder_resource(folder, folder_version, extra=extra, base=base)
        )
    )


def _datapoint_has_nested_parent(version) -> bool:
    return version.channel_id is not None or version.folder_id is not None


def _get_datapoint_parent_device_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    _parsed_id, (_datapoint, version) = required
    if _datapoint_has_nested_parent(version):
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_DEVICE))
    return _get_datapoint_device_response(
        session, datapoint_id, extra=extra, base=base
    )


def _get_datapoint_parent_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    parsed_id, (datapoint, version) = required
    if version.folder_id is not None:
        related = get_current_folder(session, version.folder_id)
        if related is None:
            return JSONAPIResponse(content=empty_related_item(_NO_TREE_PARENT))
        folder, folder_version = related
        return JSONAPIResponse(
            content=item_document(
                folder_resource(folder, folder_version, extra=extra, base=base)
            )
        )
    if version.channel_id is not None:
        related = get_current_channel(session, version.channel_id)
        if related is None:
            return JSONAPIResponse(content=empty_related_item(_NO_TREE_PARENT))
        channel, channel_version = related
        return JSONAPIResponse(
            content=item_document(
                channel_resource(channel, channel_version, extra=extra, base=base)
            )
        )
    related = current_device_for_datapoint(session, parsed_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_TREE_PARENT))
    device, device_version = related
    return JSONAPIResponse(
        content=item_document(
            serialize_device(session, device, device_version, extra=extra, base=base)
        )
    )


def _list_datapoint_children_response(
    session: Session,
    datapoint_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_datapoint(session, datapoint_id)
    if error is not None:
        return error
    return collection_from_item_dicts(
        [],
        page_number=page_number,
        page_size=page_size,
    )


def _require_group_range(session: Session, group_range_id: str):
    parsed_id = parse_resource_id(group_range_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _GROUP_RANGE_NOT_FOUND)
    current = get_current_group_range(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _GROUP_RANGE_NOT_FOUND)
    return (parsed_id, current), None


def _get_group_range_parent_response(
    session: Session,
    group_range_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_group_range(session, group_range_id)
    if error is not None:
        return error
    _parsed_id, (_group_range, version) = required
    if version.parent_group_range_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_GROUP_RANGE))
    related = get_current_group_range(session, version.parent_group_range_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_GROUP_RANGE))
    parent, parent_version = related
    return JSONAPIResponse(
        content=item_document(
            group_range_resource(parent, parent_version, extra=extra, base=base)
        )
    )


def _list_child_group_ranges_response(
    session: Session,
    group_range_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_group_range(session, group_range_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_child_group_range_pairs(session, parsed_id),
        group_range_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/datapoints")
def list_datapoints(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_datapoints_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/datapoints/{datapoint_id}")
def get_datapoint(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_datapoint_response(
        session, datapoint_id, extra=extra, base=base
    )


@read_router.get("/datapoints/{datapoint_id}/functions")
def list_datapoint_functions(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_datapoint_functions_response(
        session,
        datapoint_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@read_router.get("/datapoints/{datapoint_id}/device")
def get_datapoint_device(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_datapoint_device_response(
        session, datapoint_id, extra=extra, base=base
    )


@kss_router.get("/datapoints/{datapoint_id}/parentdevice")
def get_datapoint_parent_device(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_datapoint_parent_device_response(
        session, datapoint_id, extra=extra, base=base
    )


@kss_router.get("/datapoints/{datapoint_id}/parent")
def get_datapoint_parent(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_datapoint_parent_response(
        session, datapoint_id, extra=extra, base=base
    )


@kss_router.get("/datapoints/{datapoint_id}/children")
def list_datapoint_children(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_datapoint_children_response(
        session,
        datapoint_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_group_ranges_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_group_range_pairs(session),
        group_range_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_group_range_response(
    session: Session,
    group_range_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_group_range(session, group_range_id)
    if error is not None:
        return error
    _parsed_id, (group_range, version) = required
    return JSONAPIResponse(
        content=item_document(
            group_range_resource(group_range, version, extra=extra, base=base)
        )
    )


@kss_router.get("/datapoints/{datapoint_id}/channel")
def get_datapoint_channel(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_datapoint_channel_response(
        session, datapoint_id, extra=extra, base=base
    )


@kss_router.get("/datapoints/{datapoint_id}/folder")
def get_datapoint_folder(
    datapoint_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_datapoint_folder_response(
        session, datapoint_id, extra=extra, base=base
    )


@kss_router.get("/group-ranges")
def list_group_ranges(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_group_ranges_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/group-ranges/{group_range_id}")
def get_group_range(
    group_range_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_group_range_response(
        session, group_range_id, extra=extra, base=base
    )


@kss_router.get("/group-ranges/{group_range_id}/parentgrouprange")
def get_group_range_parent(
    group_range_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_group_range_parent_response(
        session, group_range_id, extra=extra, base=base
    )


@kss_router.get("/group-ranges/{group_range_id}/childgroupranges")
def list_child_group_ranges(
    group_range_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_child_group_ranges_response(
        session,
        group_range_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )
