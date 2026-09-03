from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.services.topology import upsert_topology_from_project
from tests.helpers import persist_area_line_segment, persist_installation

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)

TOPOLOGY_PROJECT = {
    "topology": {
        "0": {
            "name": "_IP",
            "description": None,
            "identifier": "P-040E-0_A-1",
            "ets_id": "A-1",
            "address": 0,
            "completion_status": "Accepted",
            "last_modified": None,
            "lines": {
                "0": {
                    "name": "",
                    "medium_type": "KNXnet/IP (IP)",
                    "medium_type_ref": "MT-5",
                    "description": None,
                    "devices": ["0.0.1"],
                    "identifier": "P-040E-0_L-1",
                    "ets_id": "L-1",
                    "address": 0,
                    "completion_status": "Accepted",
                    "last_modified": None,
                    "segments": [
                        {
                            "identifier": "P-040E-0_S-1",
                            "ets_id": "S-1",
                            "name": "Main segment",
                            "number": "0",
                            "medium_type_ref": "MT-5",
                            "description": None,
                            "completion_status": None,
                            "last_modified": None,
                        }
                    ],
                }
            },
        },
        "1": {
            "name": "TP",
            "description": "KNX",
            "identifier": "P-040E-0_A-4",
            "ets_id": "A-4",
            "address": 1,
            "completion_status": "Accepted",
            "lines": {
                "0": {
                    "name": "Main",
                    "medium_type": "Twisted Pair (TP)",
                    "medium_type_ref": "MT-0",
                    "description": None,
                    "devices": [],
                    "identifier": "P-040E-0_L-5",
                    "ets_id": "L-5",
                    "address": 0,
                    "segments": [
                        {
                            "identifier": "P-040E-0_S-5",
                            "ets_id": "S-5",
                            "name": "Main segment",
                            "number": "0",
                            "medium_type_ref": "MT-0",
                        }
                    ],
                }
            },
        },
    }
}


def test_upsert_areas_lines_segments(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    upsert_topology_from_project(session, installation, TOPOLOGY_PROJECT, FALLBACK)

    areas = {row.ets_id: row for row in session.scalars(select(Area)).all()}
    assert set(areas) == {"A-1", "A-4"}
    ip = max(areas["A-1"].versions, key=lambda item: item.last_modified)
    tp = max(areas["A-4"].versions, key=lambda item: item.last_modified)
    assert ip.name == "_IP"
    assert ip.address == 0
    assert ip.completion_status == "Accepted"
    assert tp.description == "KNX"
    assert tp.address == 1

    lines = {row.ets_id: row for row in session.scalars(select(Line)).all()}
    assert set(lines) == {"L-1", "L-5"}
    ip_line = max(lines["L-1"].versions, key=lambda item: item.last_modified)
    main = max(lines["L-5"].versions, key=lambda item: item.last_modified)
    assert ip_line.name is None
    assert ip_line.address == 0
    assert ip_line.area_id == areas["A-1"].id
    assert ip_line.medium_type_ets_id == "MT-5"
    assert main.name == "Main"
    assert main.area_id == areas["A-4"].id
    assert main.medium_type_ets_id == "MT-0"

    segments = {row.ets_id: row for row in session.scalars(select(Segment)).all()}
    assert set(segments) == {"S-1", "S-5"}
    first = max(segments["S-1"].versions, key=lambda item: item.last_modified)
    assert first.name == "Main segment"
    assert first.number == "0"
    assert first.line_id == lines["L-1"].id
    assert first.medium_type_ets_id == "MT-5"

    upsert_topology_from_project(session, installation, TOPOLOGY_PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(AreaVersion)) == 2
    assert session.scalar(select(func.count()).select_from(LineVersion)) == 2
    assert session.scalar(select(func.count()).select_from(SegmentVersion)) == 2


def test_missing_topology_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_area_line_segment(session, installation)
    upsert_topology_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(Area)) == 1
    assert session.scalars(select(Area)).one().ets_id == "A-1"


def test_human_medium_type_is_not_stored_as_ets_id(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    project = {
        "topology": {
            "0": {
                "ets_id": "A-9",
                "address": 0,
                "name": "A",
                "lines": {
                    "0": {
                        "ets_id": "L-9",
                        "address": 0,
                        "name": "L",
                        "medium_type": "Twisted Pair (TP)",
                        "segments": [],
                    }
                },
            }
        }
    }
    upsert_topology_from_project(session, installation, project, FALLBACK)
    line = session.scalars(select(Line)).one()
    version = max(line.versions, key=lambda item: item.last_modified)
    assert version.medium_type_ets_id is None
