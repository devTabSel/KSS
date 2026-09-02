"""JSON:API helpers matching the 3API media type and error envelope."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.responses import JSONResponse

from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionVersion, Location, LocationVersion

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
