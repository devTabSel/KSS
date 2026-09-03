"""Persist knx_master catalog snapshots from parse(include_catalog=True) master_data."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from kss.models.master import (
    Datafield,
    MasterData,
    MasterDatapointRole,
    MasterDatapointSubtype,
    MasterDatapointType,
    MasterFunctionPoint,
    MasterFunctionType,
    MasterManufacturer,
    MasterMediumType,
    MasterSpaceUsage,
    MasterTranslation,
)

_NUMBERED_TAGS = frozenset({"UnsignedInteger", "SignedInteger", "Float"})
_INTEGER_TAGS = frozenset({"UnsignedInteger", "SignedInteger"})


def upsert_master_catalog(
    session: Session, master_data: object | None
) -> MasterData | None:
    """Insert a knx_master snapshot, or no-op if (knx_id, version) already exists.

    Missing ``knx_id`` or ``version`` skips catalog persist entirely. Incomplete
    child rows (e.g. a DPT without ``size_in_bit``) are skipped, not fatal.
    """
    if not isinstance(master_data, Mapping):
        return None
    knx_id = _optional_str(master_data.get("knx_id"))
    version = _optional_int(master_data.get("version"))
    if knx_id is None or version is None:
        return None

    existing = session.scalars(
        select(MasterData).where(
            MasterData.knx_id == knx_id,
            MasterData.version == version,
        )
    ).first()
    if existing is not None:
        return existing

    snapshot = MasterData(id=uuid4(), knx_id=knx_id, version=version)
    session.add(snapshot)
    session.flush()
    snapshot_id = snapshot.id

    _flush_rows(
        session,
        MasterDatapointType,
        [
            row
            for item in _values(master_data.get("datapoint_types"))
            if (row := _datapoint_type_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterDatapointSubtype,
        [
            row
            for item in _values(master_data.get("datapoint_subtypes"))
            if (row := _datapoint_subtype_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        Datafield,
        [
            row
            for item in _values(master_data.get("datafields"))
            if (row := _datafield_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterFunctionType,
        [
            row
            for item in _values(master_data.get("function_types"))
            if (row := _function_type_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterDatapointRole,
        [
            row
            for item in _values(master_data.get("datapoint_roles"))
            if (row := _datapoint_role_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterSpaceUsage,
        [
            row
            for item in _values(master_data.get("space_usages"))
            if (row := _space_usage_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterMediumType,
        [
            row
            for item in _values(master_data.get("medium_types"))
            if (row := _medium_type_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterFunctionPoint,
        [
            row
            for item in _values(master_data.get("function_points"))
            if (row := _function_point_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterManufacturer,
        [
            row
            for item in _values(master_data.get("manufacturers"))
            if (row := _manufacturer_row(snapshot_id, item)) is not None
        ],
    )
    _flush_rows(
        session,
        MasterTranslation,
        [
            row
            for item in _list_items(master_data.get("translations"))
            if (row := _translation_row(snapshot_id, item)) is not None
        ],
    )
    return snapshot


def _flush_rows(session: Session, model: type, rows: list[dict[str, Any]]) -> None:
    if rows:
        session.execute(insert(model), rows)


def _values(raw: object) -> list[object]:
    if isinstance(raw, Mapping):
        return list(raw.values())
    return []


def _list_items(raw: object) -> list[object]:
    if isinstance(raw, list):
        return raw
    return []


def _optional_str(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _optional_int(raw: object) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _optional_numeric(raw: object) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def _as_mapping(raw: object) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    return {}


def _datapoint_type_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    text = _optional_str(data.get("text"))
    size_in_bit = _optional_int(data.get("size_in_bit"))
    if knx_id is None or text is None or size_in_bit is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "text": text,
        "code": _optional_str(data.get("code")),
        "number": _optional_int(data.get("number")),
        "size_in_bit": size_in_bit,
    }


def _datapoint_subtype_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    datapoint_type_knx_id = _optional_str(data.get("datapoint_type_knx_id"))
    if knx_id is None or datapoint_type_knx_id is None:
        return None
    is_default = data.get("is_default")
    if is_default is not None and not isinstance(is_default, bool):
        is_default = None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "datapoint_type_knx_id": datapoint_type_knx_id,
        "text": _optional_str(data.get("text")),
        "code": _optional_str(data.get("code")),
        "number": _optional_int(data.get("number")),
        "is_default": is_default,
    }


def _datafield_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    attributes = _as_mapping(data.get("attributes"))
    tag = str(data.get("tag") or "")
    title = _optional_str(attributes.get("Name")) or knx_id
    kind, enum_value_map = _datafield_kind(tag, attributes, data.get("enum_values"))
    integer: bool | None
    if tag in _INTEGER_TAGS:
        integer = True
    elif tag == "Float":
        integer = False
    else:
        integer = None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "title": title,
        "description": None,
        "datapoint_subtype_knx_id": _optional_str(data.get("datapoint_subtype_knx_id")),
        "kind": kind,
        "enum_value_map": enum_value_map,
        "unit": _optional_str(attributes.get("Unit")),
        "minimum": _optional_numeric(attributes.get("MinInclusive")),
        "maximum": _optional_numeric(attributes.get("MaxInclusive")),
        "resolution": _optional_numeric(attributes.get("Coefficient")),
        "integer": integer,
        "charset": _optional_str(attributes.get("Encoding")),
        "max_length": None,
    }


def _datafield_kind(
    tag: str,
    attributes: Mapping[str, Any],
    enum_values_raw: object,
) -> tuple[str | None, list[dict[str, int]] | None]:
    if tag == "Enumeration":
        return "enum", _enumeration_map(enum_values_raw)
    if tag == "Bit":
        cleared = _optional_str(attributes.get("Cleared"))
        set_text = _optional_str(attributes.get("Set"))
        if cleared is not None and set_text is not None:
            return "enum", [{cleared: 0, set_text: 1}]
        return None, None
    if tag == "String":
        return "string", None
    if tag in _NUMBERED_TAGS:
        return "numbered", None
    return None, None


def _enumeration_map(raw: object) -> list[dict[str, int]] | None:
    if not isinstance(raw, list):
        return None
    mapped: list[dict[str, int]] = []
    for item in raw:
        data = _as_mapping(item)
        text = _optional_str(data.get("text"))
        if text is None:
            continue
        value = _optional_int(data.get("value"))
        if value is None:
            continue
        mapped.append({text: value})
    return mapped or None


def _function_type_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "number": _optional_int(data.get("number")),
        "text": _optional_str(data.get("text")),
        "status": _optional_str(data.get("status")),
    }


def _datapoint_role_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "number": _optional_int(data.get("number")),
        "code": _optional_str(data.get("code")),
    }


def _space_usage_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "number": _optional_int(data.get("number")),
        "text": _optional_str(data.get("text")),
    }


def _medium_type_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "number": _optional_int(data.get("number")),
        "code": _optional_str(data.get("code")),
        "text": _optional_str(data.get("text")),
        "domain_address_length": _optional_int(data.get("domain_address_length")),
    }


def _function_point_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "function_type_knx_id": _optional_str(data.get("function_type_knx_id")),
        "role_knx_id": _optional_str(data.get("role_knx_id")),
        "datapoint_subtype_knx_id": _optional_str(data.get("datapoint_subtype_knx_id")),
        "characteristics": _optional_str(data.get("characteristics")),
        "text": _optional_str(data.get("text")),
    }


def _manufacturer_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "knx_manufacturer_id": _optional_int(data.get("knx_manufacturer_id")),
        "name": _optional_str(data.get("name")),
        "default_language_code": _optional_str(data.get("default_language_code")),
    }


def _translation_row(snapshot_id: UUID, item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    language_code = _optional_str(data.get("language_code"))
    attribute_name = _optional_str(data.get("attribute_name"))
    text = _optional_str(data.get("text"))
    if (
        knx_id is None
        or language_code is None
        or attribute_name is None
        or text is None
        or len(language_code.strip()) < 2
    ):
        return None
    return {
        "id": uuid4(),
        "master_data_id": snapshot_id,
        "knx_id": knx_id,
        "language_code": language_code,
        "attribute_name": attribute_name,
        "text": text,
    }
