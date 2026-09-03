from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.location import (
    Function,
    FunctionDatapoint,
    FunctionVersion,
    Location,
    LocationVersion,
)
from kss.models.topology import Line
from kss.services.locations import upsert_locations_from_project
from tests.helpers import persist_area_line_segment, persist_installation, persist_location

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)

NESTED_PROJECT = {
    "locations": {
        "00_SYS": {
            "type": "Building",
            "identifier": "P-040E-0_BP-1",
            "ets_id": "BP-1",
            "name": "00_SYS",
            "usage_id": None,
            "usage_text": "",
            "number": "00",
            "description": "Gebäude",
            "comment": "Gebäudekommentar",
            "completion_status": "Accepted",
            "default_line": "P-040E-0_L-1",
            "devices": ["1.1.1"],
            "functions": [],
            "spaces": {
                "11_UGH": {
                    "type": "Room",
                    "identifier": "P-040E-0_BP-4",
                    "ets_id": "BP-4",
                    "name": "11_UGH",
                    "usage_id": "tag:office",
                    "usage_text": "Office",
                    "number": "11",
                    "description": "Hobby",
                    "devices": ["1.2.3"],
                    "functions": ["F-1"],
                    "spaces": {},
                }
            },
        }
    },
    "functions": {
        "F-1": {
            "function_type": "FT-0",
            "group_addresses": {
                "1/2/3": {
                    "address": "1/2/3",
                    "name": "Licht",
                    "project_uid": 1,
                    "role": "DR-1",
                }
            },
            "identifier": "F-1",
            "ets_id": "F-1",
            "name": "CTL_HEC_EGD",
            "project_uid": 20568,
            "space_id": "P-040E-0_BP-4",
            "usage_text": "ignored",
        }
    },
}


def _by_ets(session: Session) -> dict[str, Location]:
    return {row.ets_id: row for row in session.scalars(select(Location)).all()}


def test_nested_building_room_and_function(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    upsert_locations_from_project(
        session, installation, NESTED_PROJECT, FALLBACK
    )

    locations = _by_ets(session)
    assert set(locations) == {"BP-1", "BP-4"}
    building = max(locations["BP-1"].versions, key=lambda item: item.last_modified)
    room = max(locations["BP-4"].versions, key=lambda item: item.last_modified)
    assert building.title == "00_SYS"
    assert building.location_type == "Building"
    assert building.at_type == ["loc:Building"]
    assert building.parent_location_id is None
    assert building.default_line_id is None
    assert building.usage is None
    assert building.completion_status == "Accepted"
    assert building.comment == "Gebäudekommentar"
    assert room.title == "11_UGH"
    assert room.location_type == "Room"
    assert room.usage == "tag:office"
    assert room.parent_location_id == locations["BP-1"].id
    assert room.default_line_id is None
    assert room.at_type == ["loc:Room"]
    assert room.last_modified == FALLBACK

    function = session.scalars(select(Function)).one()
    assert function.ets_id == "F-1"
    version = max(function.versions, key=lambda item: item.last_modified)
    assert version.title == "CTL_HEC_EGD"
    assert version.function_type_ets_id == "FT-0"
    assert version.location_id == locations["BP-4"].id
    assert version.at_type == ["core:ApplicationFunction"]
    assert session.scalar(select(func.count()).select_from(FunctionDatapoint)) == 0

    upsert_locations_from_project(
        session, installation, NESTED_PROJECT, FALLBACK
    )
    assert session.scalar(select(func.count()).select_from(LocationVersion)) == 2
    assert session.scalar(select(func.count()).select_from(FunctionVersion)) == 1


def test_ets_id_derived_from_identifier_suffix(session: Session) -> None:
    installation = persist_installation(session)
    project = {
        "locations": {
            "Gebäude": {
                "type": "Building",
                "identifier": "P-040E-0_BP-9",
                "name": "Gebäude",
                "usage_id": None,
                "usage_text": "",
                "number": "",
                "description": "",
                "devices": [],
                "functions": [],
                "spaces": {},
            }
        },
        "functions": {
            "P-040E-0_F-9": {
                "function_type": "",
                "identifier": "P-040E-0_F-9",
                "name": "",
                "space_id": "P-040E-0_BP-9",
                "group_addresses": {},
            }
        },
    }
    upsert_locations_from_project(session, installation, project, FALLBACK)
    location = session.scalars(select(Location)).one()
    assert location.ets_id == "BP-9"
    function = session.scalars(select(Function)).one()
    assert function.ets_id == "F-9"
    version = max(function.versions, key=lambda item: item.last_modified)
    assert version.title == "F-9"
    assert version.function_type_ets_id == "FT-0"
    assert version.location_id == location.id


def test_missing_locations_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_location(session, installation, ets_id="BP-99", title="bleibt")
    upsert_locations_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(Location)) == 1
    assert session.scalars(select(Location)).one().ets_id == "BP-99"


def test_invalid_location_type_is_skipped(session: Session) -> None:
    installation = persist_installation(session)
    project = {
        "locations": {
            "X": {
                "type": "Site",
                "identifier": "P-040E-0_BP-8",
                "name": "X",
                "usage_id": None,
                "usage_text": "",
                "number": "",
                "description": "",
                "devices": [],
                "functions": [],
                "spaces": {},
            }
        }
    }
    upsert_locations_from_project(session, installation, project, FALLBACK)
    version = session.scalars(select(LocationVersion)).one()
    assert version.location_type is None
    assert version.at_type is None
    assert version.title == "X"


def test_default_line_id_when_line_exists(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    persist_area_line_segment(session, installation)
    upsert_locations_from_project(
        session, installation, NESTED_PROJECT, FALLBACK
    )
    locations = _by_ets(session)
    building = max(locations["BP-1"].versions, key=lambda item: item.last_modified)
    line = session.scalars(select(Line).where(Line.ets_id == "L-1")).one()
    assert building.default_line_id == line.id
    room = max(locations["BP-4"].versions, key=lambda item: item.last_modified)
    assert room.default_line_id is None
