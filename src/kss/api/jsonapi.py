"""JSON:API helpers matching the 3API media type and error envelope."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.responses import JSONResponse

from kss.models.datapoint import Datapoint, DatapointVersion, GroupRange, GroupRangeVersion
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
from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionVersion, Location, LocationVersion
from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.models.trade import Trade, TradeVersion

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
    resource: dict[str, Any],
    *,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {"data": resource}
    if meta:
        document["meta"] = meta
    return document


def location_resource(
    location: Location,
    version: LocationVersion,
    *,
    extra: bool,
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
    item: dict[str, Any] = {
        "type": "location",
        "id": str(location.id),
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    if version.parent_location_id is not None:
        item["relationships"] = {
            "parentLocation": _resource_identifier(
                "location", version.parent_location_id
            )
        }
    return item


def function_resource(
    function: Function,
    version: FunctionVersion,
    *,
    extra: bool,
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
        "type": "function",
        "id": str(function.id),
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    if version.location_id is not None:
        item["relationships"] = {
            "functionLocation": _resource_identifier("location", version.location_id)
        }
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
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if version.order_number is not None:
        attributes["orderNumber"] = version.order_number
    if version.manufacturer is not None:
        attributes["manufacturer"] = version.manufacturer
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
    relationships: dict[str, Any] = {}
    if version.location_id is not None:
        relationships["deviceLocation"] = _resource_identifier(
            "location", version.location_id
        )
    if extra and version.segment_id is not None:
        relationships["segment"] = _resource_identifier("segment", version.segment_id)
    if relationships:
        item["relationships"] = relationships
    return item


def datapoint_resource(
    datapoint: Datapoint,
    version: DatapointVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or datapoint.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if version.comment is not None:
        attributes["comment"] = version.comment
    if version.readable is not None:
        attributes["readable"] = version.readable
    if version.writable is not None:
        attributes["writable"] = version.writable
    if extra:
        attributes["kss:etsId"] = datapoint.ets_id
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
        "type": "datapoint",
        "id": str(datapoint.id),
        "attributes": attributes,
    }
    _put_at_type(item, version.at_type)
    if extra and version.group_range_id is not None:
        item["relationships"] = {
            "groupRange": _resource_identifier("groupRange", version.group_range_id)
        }
    return item


def group_range_resource(
    group_range: GroupRange,
    version: GroupRangeVersion,
    *,
    extra: bool,
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
    item: dict[str, Any] = {
        "type": "groupRange",
        "id": str(group_range.id),
        "attributes": attributes,
    }
    if version.parent_group_range_id is not None:
        item["relationships"] = {
            "parentGroupRange": _resource_identifier(
                "groupRange", version.parent_group_range_id
            )
        }
    return item


def trade_resource(
    trade: Trade,
    version: TradeVersion,
    *,
    extra: bool,
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
    item: dict[str, Any] = {
        "type": "trade",
        "id": str(trade.id),
        "attributes": attributes,
    }
    if version.parent_trade_id is not None:
        item["relationships"] = {
            "parentTrade": _resource_identifier("trade", version.parent_trade_id)
        }
    return item


def channel_resource(
    channel: DeviceChannel,
    version: DeviceChannelVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title or channel.ets_id}
    if version.description is not None:
        attributes["description"] = version.description
    if extra:
        attributes["kss:etsId"] = channel.ets_id
        if version.catalog_ref is not None:
            attributes["kss:catalogRef"] = version.catalog_ref
    item: dict[str, Any] = {
        "type": "channel",
        "id": str(channel.id),
        "attributes": attributes,
    }
    relationships: dict[str, Any] = {
        "device": _resource_identifier("device", channel.device_id)
    }
    if version.parent_channel_id is not None:
        relationships["parentChannel"] = _resource_identifier(
            "channel", version.parent_channel_id
        )
    item["relationships"] = relationships
    return item


def folder_resource(
    folder: DeviceFolder,
    version: DeviceFolderVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.title or folder.ets_id}
    if extra:
        attributes["kss:etsId"] = folder.ets_id
    item: dict[str, Any] = {
        "type": "folder",
        "id": str(folder.id),
        "attributes": attributes,
    }
    relationships: dict[str, Any] = {
        "device": _resource_identifier("device", folder.device_id)
    }
    if version.parent_folder_id is not None:
        relationships["parentFolder"] = _resource_identifier(
            "folder", version.parent_folder_id
        )
    elif version.parent_channel_id is not None:
        relationships["parentChannel"] = _resource_identifier(
            "channel", version.parent_channel_id
        )
    item["relationships"] = relationships
    return item


def comm_object_resource(
    comm_object: CommObject,
    version: CommObjectVersion,
    *,
    extra: bool,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"title": version.name or comm_object.ets_id}
    if version.text is not None:
        attributes["description"] = version.text
    if extra:
        attributes["kss:etsId"] = comm_object.ets_id
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
        "type": "commObject",
        "id": str(comm_object.id),
        "attributes": attributes,
    }
    relationships: dict[str, Any] = {
        "device": _resource_identifier("device", comm_object.device_id)
    }
    if version.channel_id is not None:
        relationships["channel"] = _resource_identifier("channel", version.channel_id)
    if version.folder_id is not None:
        relationships["folder"] = _resource_identifier("folder", version.folder_id)
    item["relationships"] = relationships
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
