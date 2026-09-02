from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.master import (
    Datafield,
    MasterData,
    MasterDatapointSubtype,
    MasterDatapointType,
    MasterProjectType,
    MasterSpaceUsage,
    MasterTranslation,
)
from kss.services.master import upsert_master_catalog

SMALL_CATALOG = {
    "knx_id": "MD-1",
    "version": 1,
    "datapoint_types": {
        "DPT-1": {
            "knx_id": "DPT-1",
            "number": 1,
            "code": "1.xxx",
            "text": "1-bit",
            "size_in_bit": 1,
        }
    },
    "datapoint_subtypes": {
        "DPST-1-1": {
            "knx_id": "DPST-1-1",
            "datapoint_type_knx_id": "DPT-1",
            "number": 1,
            "code": "DPT_Switch",
            "text": "switch",
            "is_default": True,
        }
    },
    "datafields": {
        "DPST-1-1_F-1": {
            "knx_id": "DPST-1-1_F-1",
            "datapoint_subtype_knx_id": "DPST-1-1",
            "tag": "Bit",
            "attributes": {
                "Name": "Switch",
                "Cleared": "Off",
                "Set": "On",
            },
            "enum_values": [],
            "ref_ids": ["ignored"],
        }
    },
    "function_types": {},
    "datapoint_roles": {},
    "space_usages": {
        "SU-12": {"knx_id": "SU-12", "number": 12, "text": "Meeting room"}
    },
    "medium_types": {},
    "function_points": {},
    "manufacturers": {},
    "translations": [
        {
            "knx_id": "DPST-1-1",
            "language_code": "de-DE",
            "attribute_name": "Text",
            "text": "Schalten",
        }
    ],
}


def test_upsert_catalog_from_inline_dict_is_idempotent(session: Session) -> None:
    first = upsert_master_catalog(session, SMALL_CATALOG)
    assert first is not None
    assert first.knx_id == "MD-1"
    assert first.version == 1

    dpt = session.scalars(select(MasterDatapointType)).one()
    assert dpt.knx_id == "DPT-1"
    assert dpt.text == "1-bit"
    assert dpt.size_in_bit == 1

    dpst = session.scalars(select(MasterDatapointSubtype)).one()
    assert dpst.knx_id == "DPST-1-1"
    assert dpst.text == "switch"
    assert dpst.datapoint_type_knx_id == "DPT-1"

    datafield = session.scalars(select(Datafield)).one()
    assert datafield.knx_id == "DPST-1-1_F-1"
    assert datafield.title == "Switch"
    assert datafield.kind == "enum"
    assert datafield.enum_value_map == [{"Off": 0, "On": 1}]
    assert datafield.description is None
    assert datafield.max_length is None

    usage = session.scalars(select(MasterSpaceUsage)).one()
    assert usage.knx_id == "SU-12"
    assert usage.text == "Meeting room"

    translation = session.scalars(select(MasterTranslation)).one()
    assert translation.knx_id == "DPST-1-1"
    assert translation.language_code == "de-DE"
    assert translation.attribute_name == "Text"
    assert translation.text == "Schalten"

    assert session.scalar(select(func.count()).select_from(MasterProjectType)) == 0

    second = upsert_master_catalog(session, SMALL_CATALOG)
    assert second is not None
    assert second.id == first.id
    assert session.scalar(select(func.count()).select_from(MasterData)) == 1
    assert session.scalar(select(func.count()).select_from(MasterDatapointType)) == 1
    assert session.scalar(select(func.count()).select_from(Datafield)) == 1
    assert session.scalar(select(func.count()).select_from(MasterTranslation)) == 1

    other_version = dict(SMALL_CATALOG)
    other_version["version"] = 2
    third = upsert_master_catalog(session, other_version)
    assert third is not None
    assert third.id != first.id
    assert third.version == 2
    assert session.scalar(select(func.count()).select_from(MasterData)) == 2
    assert session.scalar(select(func.count()).select_from(MasterDatapointType)) == 2
    assert session.scalar(select(func.count()).select_from(MasterSpaceUsage)) == 2


def test_missing_master_data_skips_catalog(session: Session) -> None:
    assert upsert_master_catalog(session, None) is None
    assert upsert_master_catalog(session, {"knx_id": "MD-1"}) is None
    assert upsert_master_catalog(session, {"version": 1}) is None
    assert upsert_master_catalog(session, {"knx_id": None, "version": 1}) is None
    assert session.scalar(select(func.count()).select_from(MasterData)) == 0


def test_dpt_without_size_in_bit_is_skipped(session: Session) -> None:
    catalog = {
        "knx_id": "MD-1",
        "version": 1,
        "datapoint_types": {
            "DPT-1": {
                "knx_id": "DPT-1",
                "text": "1-bit",
                "size_in_bit": 1,
            },
            "DPT-bad": {
                "knx_id": "DPT-bad",
                "text": "missing size",
                "size_in_bit": None,
            },
        },
        "datapoint_subtypes": {},
        "datafields": {},
        "function_types": {},
        "datapoint_roles": {},
        "space_usages": {},
        "medium_types": {},
        "function_points": {},
        "manufacturers": {},
        "translations": [],
    }
    snapshot = upsert_master_catalog(session, catalog)
    assert snapshot is not None
    rows = session.scalars(select(MasterDatapointType)).all()
    assert [row.knx_id for row in rows] == ["DPT-1"]
