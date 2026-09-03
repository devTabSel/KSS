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
    current_child_folder_pairs,
    current_datapoints_for_folder,
    current_folder_pairs,
    get_current_channel,
    get_current_folder,
)
from kss.services.devices import get_current_device

kss_router = api_router()

_NO_FOLDER_DEVICE = "The folder is not related to a device."
_NO_PARENT_FOLDER = "The folder is not related to a parent folder."
_NO_PARENT_CHANNEL = "The folder is not related to a parent channel."
_NO_PARENT_DEVICE = "The folder is not a direct child of a device."
_NOT_FOUND = "folder not found"


def _require_folder(session: Session, folder_id: str):
    parsed_id = parse_resource_id(folder_id)
    if parsed_id is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    current = get_current_folder(session, parsed_id)
    if current is None:
        return None, error_response(404, "Not Found", _NOT_FOUND)
    return (parsed_id, current), None


def _list_folders_response(
    session: Session,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    return collection_from_pairs(
        current_folder_pairs(session),
        folder_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _get_folder_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    _parsed_id, (folder, version) = required
    return JSONAPIResponse(
        content=item_document(
            folder_resource(folder, version, extra=extra, base=base)
        )
    )


def _get_folder_device_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    _parsed_id, (folder, _version) = required
    related = get_current_device(session, folder.device_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_FOLDER_DEVICE))
    device, device_version = related
    return JSONAPIResponse(
        content=item_document(
            serialize_device(session, device, device_version, extra=extra, base=base)
        )
    )


def _get_folder_parent_device_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    _parsed_id, (_folder, version) = required
    if (
        version.parent_folder_id is not None
        or version.parent_channel_id is not None
    ):
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_DEVICE))
    return _get_folder_device_response(
        session, folder_id, extra=extra, base=base
    )


def _get_folder_tree_parent_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    _parsed_id, (_folder, version) = required
    if version.parent_folder_id is not None:
        return _get_folder_parent_folder_response(
            session, folder_id, extra=extra, base=base
        )
    if version.parent_channel_id is not None:
        return _get_folder_parent_channel_response(
            session, folder_id, extra=extra, base=base
        )
    return _get_folder_device_response(
        session, folder_id, extra=extra, base=base
    )


def _get_folder_parent_folder_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    _parsed_id, (_folder, version) = required
    if version.parent_folder_id is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_FOLDER))
    related = get_current_folder(session, version.parent_folder_id)
    if related is None:
        return JSONAPIResponse(content=empty_related_item(_NO_PARENT_FOLDER))
    parent, parent_version = related
    return JSONAPIResponse(
        content=item_document(
            folder_resource(parent, parent_version, extra=extra, base=base)
        )
    )


def _get_folder_parent_channel_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    _parsed_id, (_folder, version) = required
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


def _list_child_folders_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_child_folder_pairs(session, parsed_id),
        folder_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_folder_child_datapoints_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    parsed_id, _current = required
    return collection_from_pairs(
        current_datapoints_for_folder(session, parsed_id),
        datapoint_resource,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


def _list_folder_children_response(
    session: Session,
    folder_id: str,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    required, error = _require_folder(session, folder_id)
    if error is not None:
        return error
    parsed_id, _current = required
    items = [
        folder_resource(entity, version, extra=extra, base=base)
        for entity, version in current_child_folder_pairs(session, parsed_id)
    ]
    items.extend(
        datapoint_resource(entity, version, extra=extra, base=base)
        for entity, version in current_datapoints_for_folder(session, parsed_id)
    )
    return collection_from_item_dicts(
        items,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/folders")
def list_folders(
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_folders_response(
        session,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/folders/{folder_id}")
def get_folder(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_folder_response(session, folder_id, extra=extra, base=base)


@kss_router.get("/folders/{folder_id}/device")
def get_folder_device(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_folder_device_response(session, folder_id, extra=extra, base=base)


@kss_router.get("/folders/{folder_id}/parentdevice")
def get_folder_parent_device(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_folder_parent_device_response(
        session, folder_id, extra=extra, base=base
    )


@kss_router.get("/folders/{folder_id}/parent")
def get_folder_tree_parent(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_folder_tree_parent_response(
        session, folder_id, extra=extra, base=base
    )


@kss_router.get("/folders/{folder_id}/parentfolder")
def get_folder_parent_folder(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_folder_parent_folder_response(
        session, folder_id, extra=extra, base=base
    )


@kss_router.get("/folders/{folder_id}/childfolders")
def list_child_folders(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_child_folders_response(
        session,
        folder_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/folders/{folder_id}/childdatapoints")
def list_folder_child_datapoints(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_folder_child_datapoints_response(
        session,
        folder_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/folders/{folder_id}/children")
def list_folder_children(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
    page_number: PageNumber,
    page_size: PageSize,
) -> JSONAPIResponse:
    return _list_folder_children_response(
        session,
        folder_id,
        extra=extra,
        base=base,
        page_number=page_number,
        page_size=page_size,
    )


@kss_router.get("/folders/{folder_id}/parentchannel")
def get_folder_parent_channel(
    folder_id: str,
    session: SessionDep,
    extra: ExtraDep,
    base: ApiBaseDep,
) -> JSONAPIResponse:
    return _get_folder_parent_channel_response(
        session, folder_id, extra=extra, base=base
    )
