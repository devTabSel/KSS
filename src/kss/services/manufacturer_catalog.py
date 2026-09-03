"""Persist manufacturer XML catalogs from parse(include_catalog=True).

Insert-if-missing per ``knx_id`` (existing rows are not overwritten). Order:
hardware → products → hardware2programs → application_programs → comm_objects
→ refs. Missing keys skip the row, they do not abort the ingest.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from kss.models.master import (
    MasterApplicationCommObject,
    MasterApplicationCommObjectRef,
    MasterApplicationProgram,
    MasterHardware,
    MasterHardware2Program,
    MasterProduct,
)


def upsert_manufacturer_catalog(
    session: Session, manufacturer_data: object | None
) -> None:
    """Insert missing manufacturer catalog rows. No-op if ``manufacturer_data`` is absent."""
    if not isinstance(manufacturer_data, Mapping):
        return

    _upsert_hardware(session, manufacturer_data.get("hardware"))
    _upsert_products(session, manufacturer_data.get("products"))
    _upsert_hardware2programs(session, manufacturer_data.get("hardware2programs"))
    _upsert_application_programs(
        session, manufacturer_data.get("application_programs")
    )


def _upsert_hardware(session: Session, raw: object) -> None:
    incoming: list[dict[str, Any]] = []
    knx_ids: list[str] = []
    for item in _values(raw):
        row = _hardware_row(item)
        if row is None:
            continue
        knx_ids.append(row["knx_id"])
        incoming.append(row)
    existing = _existing_knx_ids(session, MasterHardware, knx_ids)
    _flush_rows(
        session,
        MasterHardware,
        [row for row in incoming if row["knx_id"] not in existing],
    )


def _upsert_products(session: Session, raw: object) -> None:
    incoming: list[dict[str, Any]] = []
    knx_ids: list[str] = []
    hardware_ids: set[str] = set()
    for item in _values(raw):
        row = _product_row(item)
        if row is None:
            continue
        knx_ids.append(row["knx_id"])
        hardware_ids.add(row["hardware_knx_id"])
        incoming.append(row)
    existing = _existing_knx_ids(session, MasterProduct, knx_ids)
    present_hardware = _existing_knx_ids(session, MasterHardware, list(hardware_ids))
    _flush_rows(
        session,
        MasterProduct,
        [
            row
            for row in incoming
            if row["knx_id"] not in existing
            and row["hardware_knx_id"] in present_hardware
        ],
    )


def _upsert_hardware2programs(session: Session, raw: object) -> None:
    incoming: list[dict[str, Any]] = []
    knx_ids: list[str] = []
    hardware_ids: set[str] = set()
    for item in _values(raw):
        row = _hardware2program_row(item)
        if row is None:
            continue
        knx_ids.append(row["knx_id"])
        hardware_ids.add(row["hardware_knx_id"])
        incoming.append(row)
    existing = _existing_knx_ids(session, MasterHardware2Program, knx_ids)
    present_hardware = _existing_knx_ids(session, MasterHardware, list(hardware_ids))
    _flush_rows(
        session,
        MasterHardware2Program,
        [
            row
            for row in incoming
            if row["knx_id"] not in existing
            and row["hardware_knx_id"] in present_hardware
        ],
    )


def _upsert_application_programs(session: Session, raw: object) -> None:
    incoming: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    knx_ids: list[str] = []
    for item in _values(raw):
        data = _as_mapping(item)
        row = _application_program_row(data)
        if row is None:
            continue
        knx_ids.append(row["knx_id"])
        incoming.append((row, data))
    existing = _existing_knx_ids(session, MasterApplicationProgram, knx_ids)
    _flush_rows(
        session,
        MasterApplicationProgram,
        [row for row, _data in incoming if row["knx_id"] not in existing],
    )
    if not knx_ids:
        return
    programs = {
        row.knx_id: row
        for row in session.scalars(
            select(MasterApplicationProgram).where(
                MasterApplicationProgram.knx_id.in_(knx_ids)
            )
        ).all()
    }
    program_ids = [row.id for row in programs.values()]
    existing_cos = _comm_objects_by_program(session, program_ids)
    co_rows: list[dict[str, Any]] = []
    for row, data in incoming:
        program = programs.get(row["knx_id"])
        if program is None:
            continue
        known = existing_cos.setdefault(program.id, {})
        for comm in _values(data.get("comm_objects")):
            co_row = _comm_object_row(program.id, comm)
            if co_row is None or co_row["knx_id"] in known:
                continue
            known[co_row["knx_id"]] = None
            co_rows.append(co_row)
    _flush_rows(session, MasterApplicationCommObject, co_rows)
    existing_cos = _comm_objects_by_program(session, program_ids)
    existing_refs = _comm_object_refs_by_program(session, program_ids)
    ref_rows: list[dict[str, Any]] = []
    for row, data in incoming:
        program = programs.get(row["knx_id"])
        if program is None:
            continue
        cos = existing_cos.get(program.id, {})
        known_refs = existing_refs.setdefault(program.id, set())
        for ref in _values(data.get("comm_object_refs")):
            ref_row = _comm_object_ref_row(program.id, ref, cos)
            if ref_row is None or ref_row["knx_id"] in known_refs:
                continue
            known_refs.add(ref_row["knx_id"])
            ref_rows.append(ref_row)
    _flush_rows(session, MasterApplicationCommObjectRef, ref_rows)


def _comm_objects_by_program(
    session: Session, program_ids: list[UUID]
) -> dict[UUID, dict[str, MasterApplicationCommObject | None]]:
    result: dict[UUID, dict[str, MasterApplicationCommObject | None]] = {}
    if not program_ids:
        return result
    rows = session.scalars(
        select(MasterApplicationCommObject).where(
            MasterApplicationCommObject.application_program_id.in_(program_ids)
        )
    ).all()
    for row in rows:
        result.setdefault(row.application_program_id, {})[row.knx_id] = row
    return result


def _comm_object_refs_by_program(
    session: Session, program_ids: list[UUID]
) -> dict[UUID, set[str]]:
    result: dict[UUID, set[str]] = {}
    if not program_ids:
        return result
    rows = session.scalars(
        select(MasterApplicationCommObjectRef).where(
            MasterApplicationCommObjectRef.application_program_id.in_(program_ids)
        )
    ).all()
    for row in rows:
        result.setdefault(row.application_program_id, set()).add(row.knx_id)
    return result


def _existing_knx_ids(session: Session, model: type, knx_ids: list[str]) -> set[str]:
    if not knx_ids:
        return set()
    return set(
        session.scalars(select(model.knx_id).where(model.knx_id.in_(knx_ids))).all()
    )


def _flush_rows(session: Session, model: type, rows: list[dict[str, Any]]) -> None:
    if rows:
        session.execute(insert(model), rows)
        session.flush()


def _values(raw: object) -> list[object]:
    if isinstance(raw, Mapping):
        return list(raw.values())
    return []


def _as_mapping(raw: object) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    return {}


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


def _hardware_row(item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    manufacturer_knx_id = _optional_str(data.get("manufacturer_knx_id"))
    if knx_id is None or manufacturer_knx_id is None:
        return None
    return {
        "id": uuid4(),
        "knx_id": knx_id,
        "name": _optional_str(data.get("name")),
        "manufacturer_knx_id": manufacturer_knx_id,
    }


def _product_row(item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    hardware_knx_id = _optional_str(data.get("hardware_knx_id"))
    if knx_id is None or hardware_knx_id is None:
        return None
    return {
        "id": uuid4(),
        "knx_id": knx_id,
        "hardware_knx_id": hardware_knx_id,
        "text": _optional_str(data.get("text")),
        "order_number": _optional_str(data.get("order_number")),
        "manufacturer": _optional_str(data.get("manufacturer")),
    }


def _hardware2program_row(item: object) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    hardware_knx_id = _optional_str(data.get("hardware_knx_id"))
    application_program_knx_id = _optional_str(data.get("application_program_knx_id"))
    if knx_id is None or hardware_knx_id is None or application_program_knx_id is None:
        return None
    return {
        "id": uuid4(),
        "knx_id": knx_id,
        "hardware_knx_id": hardware_knx_id,
        "application_program_knx_id": application_program_knx_id,
    }


def _application_program_row(data: Mapping[str, Any]) -> dict[str, Any] | None:
    knx_id = _optional_str(data.get("knx_id"))
    manufacturer_knx_id = _optional_str(data.get("manufacturer_knx_id"))
    if knx_id is None or manufacturer_knx_id is None:
        return None
    return {
        "id": uuid4(),
        "knx_id": knx_id,
        "manufacturer_knx_id": manufacturer_knx_id,
    }


def _comm_object_row(
    application_program_id: UUID, item: object
) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    return {
        "id": uuid4(),
        "application_program_id": application_program_id,
        "knx_id": knx_id,
        "number": _optional_int(data.get("number")),
        "name": _optional_str(data.get("name")),
        "text": _optional_str(data.get("text")),
        "function_text": _optional_str(data.get("function_text")),
        "object_size": _optional_str(data.get("object_size")),
        "datapoint_type_ref": _optional_str(data.get("datapoint_type_ref")),
    }


def _comm_object_ref_row(
    application_program_id: UUID,
    item: object,
    comm_objects: Mapping[str, MasterApplicationCommObject | None],
) -> dict[str, Any] | None:
    data = _as_mapping(item)
    knx_id = _optional_str(data.get("knx_id"))
    if knx_id is None:
        return None
    parent = comm_objects.get(_optional_str(data.get("comm_object_knx_id")) or "")
    return {
        "id": uuid4(),
        "application_program_id": application_program_id,
        "comm_object_id": parent.id if parent is not None else None,
        "knx_id": knx_id,
        "function_text": _optional_str(data.get("function_text")),
        "object_size": _optional_str(data.get("object_size")),
        "datapoint_type_ref": _optional_str(data.get("datapoint_type_ref")),
        "name": _optional_str(data.get("name")),
        "text": _optional_str(data.get("text")),
    }
