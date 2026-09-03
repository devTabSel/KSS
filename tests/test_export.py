from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from rdflib import URIRef
from sqlalchemy.orm import Session
from xknxproject import XKNXProj

from kss.models.installation import InstallationVersion
from kss.api.flavor import at_path_token
from kss.services.knxproj import parse_knxproj
from kss.services.knxproj_export import KNXPROJ_MEDIA_TYPE, TURTLE_MEDIA_TYPE, serialize_knxproj
from kss.services.snapshot import snapshot_installation
from kss.services.temporal import version_at
from kss.services.ttl import parse_ttl
from kss.services.ttl_export import serialize_ttl
from tests.helpers import (
    at,
    persist_area_line_segment,
    persist_comm_object,
    persist_comm_object_datapoint,
    persist_datapoint,
    persist_device,
    persist_function,
    persist_function_datapoint,
    persist_installation,
    persist_location,
    persist_trade,
    persist_trade_device,
)
from tests.wa53h10 import WA53H10_GUID, WA53H10_KNXPROJ

JSONAPI = "application/vnd.api+json"


def _seed(session: Session):
    installation = persist_installation(
        session,
        title="WA53H10",
        project_guid=UUID(WA53H10_GUID),
        last_modified=at(0),
        completion_status="Editing",
        schema_version="23",
        created_by="ETS6",
        tool_version="6.4.8718.0",
        bcu_key="4294967295",
    )
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="WA53H10 later",
            last_modified=at(2),
            group_address_style="ThreeLevel",
            completion_status="Editing",
            schema_version="23",
            created_by="ETS6",
            tool_version="6.4.8718.0",
            bcu_key="4294967295",
        )
    )
    session.flush()
    segment, line_id = persist_area_line_segment(session, installation)
    building = persist_location(
        session,
        installation,
        title="00_SYS",
        ets_id="BP-1",
        location_type="Building",
        at_type=["loc:Building"],
        default_line_id=line_id,
    )
    room = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        location_type="Room",
        usage="tag:office",
        at_type=["loc:Room"],
        parent_location_id=building.id,
    )
    device = persist_device(
        session,
        installation,
        title="UGTS_DPS1280",
        ets_id="DI-1",
        individual_address="1.0.1",
        location_id=room.id,
        segment_id=segment.id,
        product_ref="M-00A6_H-00000026-1_P-1173",
        at_type=["core:Device"],
    )
    datapoint = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        group_address=256,
        datapoint_subtype_ets_id="DPST-1-1",
        at_type=["knx:FunctionPoint"],
    )
    function = persist_function(
        session,
        installation,
        title="CTL_HEC_EGD",
        ets_id="F-1",
        location_id=room.id,
        at_type=["core:ApplicationFunction"],
    )
    persist_function_datapoint(session, function, datapoint, ets_id="GF-1", role="DR-1")
    trade = persist_trade(
        session,
        installation,
        name="BUS_DPS1280",
        ets_id="T-46",
        description="Enertex Dual Power Supply 1280",
        completion_status="Accepted",
    )
    persist_trade_device(session, trade, device)
    comm = persist_comm_object(session, device, ets_id="O-1_R-1")
    persist_comm_object_datapoint(session, comm, datapoint)
    session.flush()
    return installation, device, datapoint, trade


def _parse_turtle(turtle: str):
    with NamedTemporaryFile("w", suffix=".ttl", delete=False, encoding="utf-8") as tmp:
        tmp.write(turtle)
        path = Path(tmp.name)
    try:
        return parse_ttl(path)
    finally:
        path.unlink(missing_ok=True)


def test_version_at_picks_latest_not_after_t() -> None:
    class Row:
        def __init__(self, hour: int) -> None:
            self.last_modified = at(hour)

    rows = [Row(0), Row(2)]
    assert version_at(rows, at(1)).last_modified == at(0)
    assert version_at(rows, None).last_modified == at(2)
    assert version_at(rows, datetime(2025, 1, 1, tzinfo=UTC)) is None


def test_ttl_export_includes_knxproj_trades(session: Session) -> None:
    installation, device, datapoint, trade = _seed(session)
    snap = snapshot_installation(session, installation.id, at(1))
    assert snap is not None
    assert snap.version.title == "WA53H10"
    turtle = serialize_ttl(snap)
    parsed = _parse_turtle(turtle)
    individuals = parsed.individuals
    assert installation.ets_id in individuals
    assert device.ets_id in individuals
    assert datapoint.ets_id in individuals
    assert trade.ets_id in individuals
    assigned = parsed.graph.value(
        individuals[device.ets_id],
        URIRef("http://schema.knx.org/2020/ontology/mac#assignedTrade"),
    )
    assert str(assigned) == "BUS_DPS1280"


def test_knxproj_export_roundtrip_less_info(session: Session, tmp_path: Path) -> None:
    installation, device, _datapoint, trade = _seed(session)
    snap = snapshot_installation(session, installation.id, None)
    assert snap is not None

    lean = tmp_path / "lean.knxproj"
    lean.write_bytes(serialize_knxproj(snap, less_info=True))
    parsed_lean = parse_knxproj(lean)
    assert parsed_lean["info"]["name"] == "WA53H10 later"
    assert parsed_lean.get("trades") == {}
    assert parsed_lean["devices"]

    rich = tmp_path / "rich.knxproj"
    rich.write_bytes(serialize_knxproj(snap, less_info=False))
    parsed_rich = parse_knxproj(rich)
    assert "trades" in parsed_rich
    assert trade.ets_id in parsed_rich["trades"]
    assert parsed_rich["info"]["bcu_key"] == "4294967295"
    del device


def test_get_v1_file_accept_is_not_acceptable(
    client: TestClient, session: Session
) -> None:
    installation, *_ = _seed(session)
    response = client.get(
        f"/api/v1/installations/{installation.id}",
        headers={"Accept": TURTLE_MEDIA_TYPE},
    )
    assert response.status_code == 406
    knxproj = client.get(
        f"/api/v1/installations/{installation.id}",
        params={"format": "knxproj"},
    )
    assert knxproj.status_code == 406


def test_get_kss_ttl_and_knxproj(client: TestClient, session: Session) -> None:
    installation, _device, _datapoint, trade = _seed(session)
    ttl = client.get(
        f"/api/kss/{at_path_token(at(1))}/installations/{installation.id}",
        headers={"Accept": TURTLE_MEDIA_TYPE},
    )
    assert ttl.status_code == 200
    assert TURTLE_MEDIA_TYPE in ttl.headers["content-type"]
    assert "attachment" in ttl.headers["content-disposition"]
    assert trade.ets_id in ttl.text
    assert "WA53H10" in ttl.text
    assert "WA53H10 later" not in ttl.text

    knxproj = client.get(
        f"/api/kss/installations/{installation.id}",
        params={"format": ".knxproj", "less_info": "false"},
    )
    assert knxproj.status_code == 200
    assert KNXPROJ_MEDIA_TYPE in knxproj.headers["content-type"]
    assert knxproj.content[:2] == b"PK"

    json_at = client.get(
        f"/api/kss/{at_path_token(at(1))}/installations/{installation.id}",
    )
    assert json_at.status_code == 200
    assert JSONAPI in json_at.headers["content-type"]
    assert json_at.json()["data"]["attributes"]["title"] == "WA53H10"


def _ha_parse(path: Path):
    """Home Assistant KNX integration: XKNXProj(...).parse() with defaults."""
    return XKNXProj(path).parse()


def _assert_ha_project(project, *, title: str, device_ia: str, ga: str) -> None:
    assert project["info"]["name"] == title
    assert project["info"]["group_address_style"] == "ThreeLevel"
    assert "trades" not in project
    assert "master_data" not in project
    assert device_ia in project["devices"]
    assert ga in project["group_addresses"]
    assert project["group_addresses"][ga]["name"]
    assert project["locations"]


def test_get_kss_accept_knxproj_parses_with_ha_xknxproject(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    installation, *_ = _seed(session)
    headers = (
        KNXPROJ_MEDIA_TYPE,
        "application/x-knxproj",
        "application/zip",
    )
    for index, accept in enumerate(headers):
        response = client.get(
            f"/api/kss/installations/{installation.id}",
            headers={"Accept": accept},
        )
        assert response.status_code == 200, accept
        assert KNXPROJ_MEDIA_TYPE in response.headers["content-type"]
        assert response.content[:2] == b"PK"
        path = tmp_path / f"accept-{index}.knxproj"
        path.write_bytes(response.content)
        with ZipFile(path) as archive:
            names = {name.replace("\\", "/") for name in archive.namelist()}
        assert "knx_master.xml" in names
        assert any(name.endswith(".signature") for name in names)
        project = _ha_parse(path)
        _assert_ha_project(
            project,
            title="WA53H10 later",
            device_ia="1.0.1",
            ga="0/1/0",
        )


@pytest.mark.skipif(not WA53H10_KNXPROJ.is_file(), reason="WA53H10.knxproj missing")
def test_wa53h10_http_export_parses_with_ha_xknxproject(
    client: TestClient, tmp_path: Path
) -> None:
    original = _ha_parse(WA53H10_KNXPROJ)
    ingested = client.patch(
        "/api/kss/installations",
        files={
            "file": (
                "WA53H10.knxproj",
                WA53H10_KNXPROJ.read_bytes(),
                "application/octet-stream",
            )
        },
    )
    assert ingested.status_code in {201, 204}
    collection = client.get("/api/kss/installations")
    installation_id = next(
        item["id"]
        for item in collection.json()["data"]
        if item["attributes"]["kss:projectGuid"] == WA53H10_GUID
    )
    exported = client.get(
        f"/api/kss/installations/{installation_id}",
        headers={"Accept": KNXPROJ_MEDIA_TYPE},
    )
    assert exported.status_code == 200
    path = tmp_path / "wa53h10-export.knxproj"
    path.write_bytes(exported.content)
    project = _ha_parse(path)
    assert project["info"]["guid"] == original["info"]["guid"]
    assert project["info"]["name"] == original["info"]["name"]
    assert project["info"]["group_address_style"] == original["info"]["group_address_style"]
    assert len(project["devices"]) == len(original["devices"])
    assert len(project["group_addresses"]) == len(original["group_addresses"])
    assert set(project["devices"]) == set(original["devices"])
    assert set(project["group_addresses"]) == set(original["group_addresses"])
    assert {
        addr: (ga["name"], ga["dpt"])
        for addr, ga in project["group_addresses"].items()
    } == {
        addr: (ga["name"], ga["dpt"])
        for addr, ga in original["group_addresses"].items()
    }
    assert {
        ia: device["name"] for ia, device in project["devices"].items()
    } == {
        ia: device["name"] for ia, device in original["devices"].items()
    }
    assert project["communication_objects"]
    assert project["locations"]
    catalogued = [
        device
        for device in project["devices"].values()
        if device["manufacturer_name"] or device["hardware_name"] or device["order_number"]
    ]
    assert catalogued, "exported devices should resolve manufacturer catalog names"
    for ia, device in project["devices"].items():
        original_device = original["devices"][ia]
        if original_device["manufacturer_name"]:
            assert device["manufacturer_name"] == original_device["manufacturer_name"]
        if original_device["hardware_name"]:
            assert device["hardware_name"] == original_device["hardware_name"]
        if original_device["order_number"]:
            assert device["order_number"] == original_device["order_number"]


def test_get_export_errors(client: TestClient, session: Session) -> None:
    installation, *_ = _seed(session)
    bad_at = client.get(
        f"/api/kss/not-a-date/installations/{installation.id}",
        params={"format": "ttl"},
    )
    assert bad_at.status_code == 422
    bad_format = client.get(
        f"/api/kss/installations/{installation.id}",
        params={"format": "pdf"},
    )
    assert bad_format.status_code == 422
