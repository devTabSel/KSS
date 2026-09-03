"""JSON:API helpers matching the 3API media type and error envelope."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from kss.models.device import (
    CommObject,
    CommObjectVersion,
    Device,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceFolder,
    DeviceFolderVersion,
    DeviceVersion,
)
from kss.models.group_address import GroupAddress, GroupAddressVersion, GroupRange, GroupRangeVersion
from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionVersion, Location, LocationVersion
from kss.models.master import MasterProduct
from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.models.trade import Trade, TradeVersion
from kss.services.devices import products_for_versions

JSONAPI_CONTENT_TYPE = "application/vnd.api+json"


class JSONAPIResponse(JSONResponse):
    media_type = JSONAPI_CONTENT_TYPE


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def error_body(status: int, title: str, detail: str) -> dict[str, Any]:
    return {
        "errors": [
            {
                "title": title,
                "status": str(status),
                "detail": detail,
            }
        ]
    }


def error_response(status: int, title: str, detail: str) -> JSONAPIResponse:
    return JSONAPIResponse(
        status_code=status,
        content=error_body(status, title, detail),
    )


def installation_resource(
    installation: Installation,
    version: InstallationVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title}
    if version.comment is not None:
        attributes["comment"] = version.comment
    if version.contract_number is not None:
        attributes["contractNumber"] = version.contract_number
    if version.last_modified is not None:
        attributes["lastModified"] = isoformat_utc(version.last_modified)
    if version.project_installation_number is not None:
        attributes["projectInstallationNumber"] = version.project_installation_number
    if version.completion_status is not None:
        attributes["state"] = version.completion_status
    if extra:
        if installation.ets_id is not None:
            attributes["kss:etsId"] = installation.ets_id
        if installation.project_guid is not None:
            attributes["kss:projectGuid"] = str(installation.project_guid)
        if version.group_address_style is not None:
            attributes["kss:groupAddressStyle"] = version.group_address_style
        if version.master_data_version is not None:
            attributes["kss:masterDataVersion"] = version.master_data_version
        if version.project_type is not None:
            attributes["kss:projectType"] = version.project_type
        attributes["kss:lastImport"] = isoformat_utc(installation.last_import)
        if installation.project_start is not None:
            attributes["kss:projectStart"] = isoformat_utc(installation.project_start)
        if version.schema_version is not None:
            attributes["kss:schemaVersion"] = version.schema_version
        if version.created_by is not None:
            attributes["kss:createdBy"] = version.created_by
        if version.tool_version is not None:
            attributes["kss:toolVersion"] = version.tool_version
    item: dict[str, Any] = {
        "type": "installation",
        "id": str(installation.id),
        "attributes": attributes,
    }
    return item


def collection_document(
    items: list[dict[str, Any]],
    *,
    number: int,
    size: int,
    total: int,
) -> dict[str, Any]:
    return {
        "meta": {
            "collection": {
                "number": number,
                "size": size,
                "total": total,
            }
        },
        "data": items,
    }


def item_document(
    resource: dict[str, Any] | None,
    *,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {"data": resource}
    if meta:
        document["meta"] = meta
    return document


def slice_page[T](
    rows: list[T], page_number: int, page_size: int
) -> tuple[list[T], int]:
    total = len(rows)
    start = page_number * page_size
    return rows[start : start + page_size], total


def collection_from_pairs(
    rows: list[tuple[Any, Any]],
    resource_fn,
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    page, total = slice_page(rows, page_number, page_size)
    items = [
        resource_fn(entity, version, extra=extra, base=base)
        for entity, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def collection_from_item_dicts(
    items: list[dict[str, Any]],
    *,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    """Paginated collection of already-serialized JSON:API resources (mixed types)."""
    page, total = slice_page(items, page_number, page_size)
    return JSONAPIResponse(
        content=collection_document(
            page,
            number=page_number,
            size=len(page),
            total=total,
        )
    )


def device_collection_from_pairs(
    session: Session,
    rows: list[tuple[Device, DeviceVersion]],
    *,
    extra: bool,
    base: str,
    page_number: int,
    page_size: int,
) -> JSONAPIResponse:
    page, total = slice_page(rows, page_number, page_size)
    products = products_for_versions(session, [version for _, version in page])
    items = [
        device_resource(
            device,
            version,
            extra=extra,
            base=base,
            product=_product_for(version, products),
        )
        for device, version in page
    ]
    return JSONAPIResponse(
        content=collection_document(
            items,
            number=page_number,
            size=len(items),
            total=total,
        )
    )


def serialize_device(
    session: Session,
    device: Device,
    version: DeviceVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    products = products_for_versions(session, [version])
    return device_resource(
        device,
        version,
        extra=extra,
        base=base,
        product=_product_for(version, products),
    )


def _product_for(
    version: DeviceVersion, products: dict[str, MasterProduct]
) -> MasterProduct | None:
    if version.product_ref is None:
        return None
    return products.get(version.product_ref)


def related_href(base: str, *parts: str) -> str:
    """Mount-prefixed related URL. ``base`` is ``/api/v1`` or ``/api/kss``."""
    return "/".join((base.rstrip("/"), *(str(part).strip("/") for part in parts)))


def related_links_member(related: str) -> dict[str, Any]:
    """3API ``relatedLinksMember.json``: ``links.related``, never a resource identifier."""
    return {"links": {"related": related}}


def empty_related_item(nodata: str) -> dict[str, Any]:
    """To-one nested GET when the primary exists but the target does not (``Location.json``)."""
    return item_document(None, meta={"nodata": nodata})


def location_resource(
    location: Location,
    version: LocationVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if extra:
        attributes["kss:etsId"] = location.ets_id
        if version.location_type is not None:
            attributes["kss:locationType"] = version.location_type
        if version.usage is not None:
            attributes["kss:usage"] = version.usage
        if version.number is not None:
            attributes["kss:number"] = version.number
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
    loc = str(location.id)
    item: dict[str, Any] = {
        "type": "location",
        "id": loc,
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    item["relationships"] = {
        "parentLocation": related_links_member(
            related_href(base, "locations", loc, "parentlocation")
        ),
        "childLocations": related_links_member(
            related_href(base, "locations", loc, "childlocations")
        ),
        "locationFunctions": related_links_member(
            related_href(base, "locations", loc, "functions")
        ),
        "locationDevices": related_links_member(
            related_href(base, "locations", loc, "devices")
        ),
    }
    return item


def function_resource(
    function: GroupAddress,
    version: GroupAddressVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or function.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if extra:
        attributes["kss:etsId"] = function.ets_id
        if version.group_address is not None:
            attributes["kss:groupAddress"] = version.group_address
        if version.datapoint_subtype_ets_id is not None:
            attributes["kss:datapointSubtype"] = version.datapoint_subtype_ets_id
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
        if version.security is not None:
            attributes["kss:security"] = version.security
        if version.unfiltered is not None:
            attributes["kss:unfiltered"] = version.unfiltered
        if version.central is not None:
            attributes["kss:central"] = version.central
        if version.global_ is not None:
            attributes["kss:global"] = version.global_
        if version.purpose is not None:
            attributes["kss:purpose"] = version.purpose
        if version.key is not None:
            attributes["kss:key"] = version.key
    item: dict[str, Any] = {
        "type": "function",
        "id": str(function.id),
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    function_id = str(function.id)
    relationships: dict[str, Any] = {
        "functionLocation": related_links_member(
            related_href(base, "functions", function_id, "location")
        ),
        "functionDatapoints": related_links_member(
            related_href(base, "functions", function_id, "datapoints")
        ),
    }
    if extra:
        relationships["groupRange"] = related_links_member(
            related_href(base, "functions", function_id, "group-range")
        )
    item["relationships"] = relationships
    return item


def area_resource(
    area: Area,
    version: AreaVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or area.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if extra:
        attributes["kss:etsId"] = area.ets_id
        attributes["kss:address"] = version.address
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
    return {
        "type": "area",
        "id": str(area.id),
        "attributes": attributes,
    }


def line_resource(
    line: Line,
    version: LineVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or line.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if extra:
        attributes["kss:etsId"] = line.ets_id
        attributes["kss:address"] = version.address
        if version.medium_type_ets_id is not None:
            attributes["kss:mediumType"] = version.medium_type_ets_id
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
    item: dict[str, Any] = {
        "type": "line",
        "id": str(line.id),
        "attributes": attributes,
    }
    item["relationships"] = {
        "area": _resource_identifier("area", version.area_id)
    }
    return item


def segment_resource(
    segment: Segment,
    version: SegmentVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or segment.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if extra:
        attributes["kss:etsId"] = segment.ets_id
        if version.number is not None:
            attributes["kss:number"] = version.number
        if version.medium_type_ets_id is not None:
            attributes["kss:mediumType"] = version.medium_type_ets_id
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
    item: dict[str, Any] = {
        "type": "segment",
        "id": str(segment.id),
        "attributes": attributes,
    }
    item["relationships"] = {
        "line": _resource_identifier("line", version.line_id)
    }
    return item


def device_resource(
    device: Device,
    version: DeviceVersion,
    *,
    extra: bool,
    base: str,
    product: MasterProduct | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if product is not None:
        if product.order_number is not None:
            attributes["orderNumber"] = product.order_number
        if product.manufacturer is not None:
            attributes["manufacturer"] = product.manufacturer
    attributes["lastModified"] = isoformat_utc(version.last_modified)
    if version.last_downloaded is not None:
        attributes["lastDownloaded"] = isoformat_utc(version.last_downloaded)
    if version.serial_number is not None:
        attributes["serialNumber"] = version.serial_number
    if version.individual_address is not None:
        attributes["individualAddress"] = version.individual_address
    version_attrs: dict[str, Any] = {}
    if version.firmware_version is not None:
        version_attrs["firmware"] = version.firmware_version
    if version.hardware_version is not None:
        version_attrs["hardware"] = version.hardware_version
    if version_attrs:
        attributes["version"] = version_attrs
    if extra:
        attributes["kss:etsId"] = device.ets_id
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
        if version.product_ref is not None:
            attributes["kss:productRef"] = version.product_ref
        if version.hardware_program_ref is not None:
            attributes["kss:hardwareProgramRef"] = version.hardware_program_ref
        if version.application_program_ref is not None:
            attributes["kss:applicationProgramRef"] = version.application_program_ref
        if version.communication_part_loaded is not None:
            attributes["kss:communicationPartLoaded"] = (
                version.communication_part_loaded
            )
        if version.individual_address_loaded is not None:
            attributes["kss:individualAddressLoaded"] = (
                version.individual_address_loaded
            )
        if version.application_program_loaded is not None:
            attributes["kss:applicationProgramLoaded"] = (
                version.application_program_loaded
            )
        if version.parameters_loaded is not None:
            attributes["kss:parametersLoaded"] = version.parameters_loaded
        if version.medium_config_loaded is not None:
            attributes["kss:mediumConfigLoaded"] = version.medium_config_loaded
        if version.bus_current is not None:
            attributes["kss:busCurrent"] = version.bus_current
        if version.installation_hints is not None:
            attributes["kss:installationHints"] = version.installation_hints
        if version.assigned_trade is not None:
            attributes["kss:assignedTrade"] = version.assigned_trade
        if version.operates_for_trade:
            attributes["kss:operatesForTrade"] = list(version.operates_for_trade)
    item: dict[str, Any] = {
        "type": "device",
        "id": str(device.id),
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    device_id = str(device.id)
    relationships: dict[str, Any] = {
        "deviceLocation": related_links_member(
            related_href(base, "devices", device_id, "location")
        ),
        "deviceDatapoints": related_links_member(
            related_href(base, "devices", device_id, "datapoints")
        ),
    }
    if extra and version.segment_id is not None:
        relationships["segment"] = _resource_identifier(
            "segment", version.segment_id
        )
    item["relationships"] = relationships
    return item


def datapoint_resource(
    datapoint: CommObject,
    version: CommObjectVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or datapoint.ets_id}
    if version.text is not None:
        attributes["description"] = version.text
    if version.read_flag is not None:
        attributes["readable"] = version.read_flag
    if version.write_flag is not None:
        attributes["writable"] = version.write_flag
    if extra:
        attributes["kss:etsId"] = datapoint.ets_id
        if version.number is not None:
            attributes["kss:number"] = version.number
        if version.datapoint_subtype_ets_id is not None:
            attributes["kss:datapointSubtype"] = version.datapoint_subtype_ets_id
        if version.communication_flag is not None:
            attributes["kss:communicationFlag"] = version.communication_flag
        if version.read_flag is not None:
            attributes["kss:readFlag"] = version.read_flag
        if version.write_flag is not None:
            attributes["kss:writeFlag"] = version.write_flag
        if version.transmit_flag is not None:
            attributes["kss:transmitFlag"] = version.transmit_flag
        if version.update_flag is not None:
            attributes["kss:updateFlag"] = version.update_flag
        if version.read_on_init_flag is not None:
            attributes["kss:readOnInitFlag"] = version.read_on_init_flag
        if version.priority is not None:
            attributes["kss:priority"] = version.priority
    item: dict[str, Any] = {
        "type": "datapoint",
        "id": str(datapoint.id),
        "attributes": attributes,
    }
    datapoint_id = str(datapoint.id)
    relationships: dict[str, Any] = {
        "datapointFunctions": related_links_member(
            related_href(base, "datapoints", datapoint_id, "functions")
        ),
        "datapointDevice": related_links_member(
            related_href(base, "datapoints", datapoint_id, "device")
        ),
    }
    if extra:
        relationships["channel"] = related_links_member(
            related_href(base, "datapoints", datapoint_id, "channel")
        )
        relationships["folder"] = related_links_member(
            related_href(base, "datapoints", datapoint_id, "folder")
        )
        relationships["parentDevice"] = related_links_member(
            related_href(base, "datapoints", datapoint_id, "parentdevice")
        )
        relationships["parent"] = related_links_member(
            related_href(base, "datapoints", datapoint_id, "parent")
        )
        relationships["children"] = related_links_member(
            related_href(base, "datapoints", datapoint_id, "children")
        )
    item["relationships"] = relationships
    return item


def application_function_resource(
    function: Function,
    version: FunctionVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if extra:
        attributes["kss:etsId"] = function.ets_id
        attributes["kss:functionType"] = version.function_type_ets_id
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
    item: dict[str, Any] = {
        "type": "applicationFunction",
        "id": str(function.id),
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    function_id = str(function.id)
    item["relationships"] = {
        "location": related_links_member(
            related_href(base, "application-functions", function_id, "location")
        ),
        "functions": related_links_member(
            related_href(base, "application-functions", function_id, "functions")
        ),
    }
    return item


def group_range_resource(
    group_range: GroupRange,
    version: GroupRangeVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or group_range.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if extra:
        attributes["kss:etsId"] = group_range.ets_id
        if version.range_start is not None:
            attributes["kss:rangeStart"] = version.range_start
        if version.range_end is not None:
            attributes["kss:rangeEnd"] = version.range_end
        if version.unfiltered is not None:
            attributes["kss:unfiltered"] = version.unfiltered
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
        if version.security is not None:
            attributes["kss:security"] = version.security
    range_id = str(group_range.id)
    item: dict[str, Any] = {
        "type": "groupRange",
        "id": range_id,
        "attributes": attributes,
    }
    item["relationships"] = {
        "parentGroupRange": related_links_member(
            related_href(base, "group-ranges", range_id, "parentgrouprange")
        ),
        "childGroupRanges": related_links_member(
            related_href(base, "group-ranges", range_id, "childgroupranges")
        ),
    }
    return item


def trade_resource(
    trade: Trade,
    version: TradeVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if extra:
        attributes["kss:etsId"] = trade.ets_id
        if version.number is not None:
            attributes["kss:number"] = version.number
        if version.completion_status is not None:
            attributes["kss:completionStatus"] = version.completion_status
    trade_id = str(trade.id)
    item: dict[str, Any] = {
        "type": "trade",
        "id": trade_id,
        "attributes": attributes,
    }
    item["relationships"] = {
        "parentTrade": related_links_member(
            related_href(base, "trades", trade_id, "parenttrade")
        ),
        "childTrades": related_links_member(
            related_href(base, "trades", trade_id, "childtrades")
        ),
        "tradeDevices": related_links_member(
            related_href(base, "trades", trade_id, "devices")
        ),
    }
    return item


def channel_resource(
    channel: DeviceChannel,
    version: DeviceChannelVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title or channel.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if extra:
        attributes["kss:etsId"] = channel.ets_id
        if version.catalog_ref is not None:
            attributes["kss:catalogRef"] = version.catalog_ref
    channel_id = str(channel.id)
    item: dict[str, Any] = {
        "type": "channel",
        "id": channel_id,
        "attributes": attributes,
    }
    item["relationships"] = {
        "device": related_links_member(
            related_href(base, "channels", channel_id, "device")
        ),
        "parentDevice": related_links_member(
            related_href(base, "channels", channel_id, "parentdevice")
        ),
        "parentChannel": related_links_member(
            related_href(base, "channels", channel_id, "parentchannel")
        ),
        "parent": related_links_member(
            related_href(base, "channels", channel_id, "parent")
        ),
        "childChannels": related_links_member(
            related_href(base, "channels", channel_id, "childchannels")
        ),
        "childFolders": related_links_member(
            related_href(base, "channels", channel_id, "childfolders")
        ),
        "childDatapoints": related_links_member(
            related_href(base, "channels", channel_id, "childdatapoints")
        ),
        "children": related_links_member(
            related_href(base, "channels", channel_id, "children")
        ),
    }
    return item


def folder_resource(
    folder: DeviceFolder,
    version: DeviceFolderVersion,
    *,
    extra: bool,
    base: str,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title or folder.ets_id}
    if extra:
        attributes["kss:etsId"] = folder.ets_id
    folder_id = str(folder.id)
    item: dict[str, Any] = {
        "type": "folder",
        "id": folder_id,
        "attributes": attributes,
    }
    item["relationships"] = {
        "device": related_links_member(
            related_href(base, "folders", folder_id, "device")
        ),
        "parentDevice": related_links_member(
            related_href(base, "folders", folder_id, "parentdevice")
        ),
        "parentFolder": related_links_member(
            related_href(base, "folders", folder_id, "parentfolder")
        ),
        "parentChannel": related_links_member(
            related_href(base, "folders", folder_id, "parentchannel")
        ),
        "parent": related_links_member(
            related_href(base, "folders", folder_id, "parent")
        ),
        "childFolders": related_links_member(
            related_href(base, "folders", folder_id, "childfolders")
        ),
        "childDatapoints": related_links_member(
            related_href(base, "folders", folder_id, "childdatapoints")
        ),
        "children": related_links_member(
            related_href(base, "folders", folder_id, "children")
        ),
    }
    return item


def parse_resource_id(resource_id: str) -> UUID | None:
    try:
        return UUID(resource_id)
    except ValueError:
        return None


parse_installation_id = parse_resource_id


def _put_at_type(item: dict[str, Any], at_type: list[str] | None) -> None:
    if at_type:
        item["meta"] = {"@type": list(at_type)}


def _resource_identifier(resource_type: str, resource_id: UUID) -> dict[str, Any]:
    return {"data": {"type": resource_type, "id": str(resource_id)}}
