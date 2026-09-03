from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.datapoint import Datapoint, DatapointVersion, GroupRange, GroupRangeVersion
from kss.models.location import FunctionDatapoint
from kss.services.datapoints import upsert_datapoints_from_project
from kss.services.locations import upsert_locations_from_project
from tests.helpers import persist_datapoint, persist_installation

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)

DATAPOINT_PROJECT = {
    "locations": {
        "00_SYS": {
            "type": "Building",
            "identifier": "P-040E-0_BP-1",
            "ets_id": "BP-1",
            "name": "00_SYS",
            "devices": [],
            "functions": ["F-1"],
            "spaces": {},
        }
    },
    "functions": {
        "F-1": {
            "function_type": "FT-0",
            "group_addresses": {
                "0/1/0": {
                    "address": "0/1/0",
                    "name": "Licht schalten",
                    "project_uid": 1,
                    "role": "DR-1",
                    "identifier": "P-040E-0_GF-1",
                    "ets_id": "GF-1",
                    "ga_ets_id": "GA-1",
                    "ref_id": "GA-1",
                }
            },
            "identifier": "F-1",
            "ets_id": "F-1",
            "name": "CTL_HEC_EGD",
            "project_uid": 20568,
            "space_id": "P-040E-0_BP-1",
            "usage_text": "",
        }
    },
    "group_ranges": {
        "0": {
            "name": "Haupt",
            "address_start": 0,
            "address_end": 2047,
            "comment": "",
            "group_addresses": [],
            "group_ranges": {
                "0/1": {
                    "name": "Licht",
                    "address_start": 256,
                    "address_end": 511,
                    "comment": "",
                    "group_addresses": ["0/1/0"],
                    "group_ranges": {},
                    "identifier": "P-040E-0_GR-1",
                    "ets_id": "GR-1",
                    "description": None,
                    "completion_status": None,
                    "last_modified": None,
                    "unfiltered": None,
                    "security": None,
                }
            },
            "identifier": "P-040E-0_GR-0",
            "ets_id": "GR-0",
            "description": None,
            "completion_status": None,
            "last_modified": None,
            "unfiltered": None,
            "security": None,
        }
    },
    "group_addresses": {
        "0/1/0": {
            "name": "Licht schalten",
            "identifier": "GA-1",
            "raw_address": 256,
            "address": "0/1/0",
            "project_uid": 1,
            "dpt": {"main": 1, "sub": 1},
            "data_secure": False,
            "communication_object_ids": [],
            "description": "Schaltbefehl",
            "comment": "",
            "ets_id": "GA-1",
            "datapoint_type_ref": "DPST-1-1",
            "completion_status": "Accepted",
            "last_modified": None,
            "unfiltered": None,
            "central": None,
            "global_": None,
            "purpose": None,
            "security": None,
            "key": None,
        }
    },
}


def test_upsert_datapoint_group_range_and_function_edge(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    upsert_locations_from_project(session, installation, DATAPOINT_PROJECT, FALLBACK)
    upsert_datapoints_from_project(session, installation, DATAPOINT_PROJECT, FALLBACK)

    ranges = {row.ets_id: row for row in session.scalars(select(GroupRange)).all()}
    assert set(ranges) == {"GR-0", "GR-1"}
    parent = max(ranges["GR-0"].versions, key=lambda item: item.last_modified)
    child = max(ranges["GR-1"].versions, key=lambda item: item.last_modified)
    assert parent.parent_group_range_id is None
    assert parent.range_start == 0
    assert child.parent_group_range_id == ranges["GR-0"].id
    assert child.name == "Licht"

    datapoint = session.scalars(select(Datapoint)).one()
    assert datapoint.ets_id == "GA-1"
    version = max(datapoint.versions, key=lambda item: item.last_modified)
    assert version.name == "Licht schalten"
    assert version.group_address == 256
    assert version.datapoint_subtype_ets_id == "DPST-1-1"
    assert version.at_type == ["knx:FunctionPoint"]
    assert version.completion_status == "Accepted"
    assert version.group_range_id == ranges["GR-1"].id

    edge = session.scalars(select(FunctionDatapoint)).one()
    assert edge.ets_id == "GF-1"
    assert edge.role == "DR-1"
    assert edge.linked is True
    assert edge.datapoint_id == datapoint.id

    upsert_datapoints_from_project(session, installation, DATAPOINT_PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(DatapointVersion)) == 1
    assert session.scalar(select(func.count()).select_from(GroupRangeVersion)) == 2
    assert session.scalar(select(func.count()).select_from(FunctionDatapoint)) == 1


def test_missing_group_addresses_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_datapoint(session, installation, ets_id="GA-99")
    upsert_datapoints_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(Datapoint)) == 1
    assert session.scalars(select(Datapoint)).one().ets_id == "GA-99"
