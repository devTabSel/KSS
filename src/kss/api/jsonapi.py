"""JSON:API helpers matching the 3API media type and error envelope."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.responses import JSONResponse

from kss.models.installation import Installation, InstallationVersion

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
        if installation.installation_index is not None:
            attributes["kss:installationIndex"] = installation.installation_index
        if installation.group_address_style is not None:
            attributes["kss:groupAddressStyle"] = installation.group_address_style
        if version.master_data_version is not None:
            attributes["kss:masterDataVersion"] = version.master_data_version
        if version.project_type is not None:
            attributes["kss:projectType"] = version.project_type
        attributes["kss:lastImport"] = isoformat_utc(installation.last_import)
    item: dict[str, Any] = {
        "type": "installation",
        "id": str(installation.id),
        "attributes": attributes,
    }
    if version.type_description is not None:
        item["meta"] = {"typedescription": version.type_description}
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


def parse_installation_id(installation_id: str) -> UUID | None:
    try:
        return UUID(installation_id)
    except ValueError:
        return None
