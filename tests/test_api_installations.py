from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.db import get_session
from kss.main import app
from kss.models.bus_bindings import BusGaBinding, BusPaBinding
from kss.models.datapoint import Datapoint, DatapointVersion, GroupRange, GroupRangeVersion
from kss.models.device import (
    CommObject,
    CommObjectDatapoint,
    CommObjectVersion,
    Device,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceFolder,
    DeviceFolderVersion,
    DeviceVersion,
)
from kss.models.location import Function, FunctionDatapoint, Location, LocationVersion
from kss.models.master import MasterData, MasterDatapointSubtype, MasterTranslation
from kss.models.topology import Area, Line, Segment
from kss.models.trade import Trade, TradeDevice, TradeVersion
from tests.helpers import persist_installation
from tests.wa53h10 import (
    ETS6_FREE_KNXPROJ,
    WA53H10_ETS_ID,
    WA53H10_GUID,
    WA53H10_KNXPROJ,
    write_wa53h10_installation_knxproj,
)

import pytest

JSONAPI = "application/vnd.api+json"

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
TEST_A1_TTL = WORKSPACE_ROOT / "research" / "test_A 1 all objects #1.ttl"
TEST_A1_GUID = "d0eb6c35-7a1e-41dd-8832-105ae1964af1"


def _kss_keys(attributes: dict) -> set[str]:
    return {key for key in attributes if key.startswith("kss:")}


def test_empty_collection_has_pagination_meta(client: TestClient) -> None:
    response = client.get("/api/v1/installations")
    assert response.status_code == 200
    assert JSONAPI in response.headers["content-type"]
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["collection"] == {"number": 0, "size": 0, "total": 0}


def test_get_v1_omits_kss_attributes(client: TestClient, session: Session) -> None:
    installation = persist_installation(
        session,
        title="WA53H10",
        project_start=datetime(2021, 12, 3, 11, 17, 25, 540603, tzinfo=UTC),
        schema_version="23",
        created_by="ETS6",
        tool_version="6.4.8718.0",
        bcu_key="123456",
        ip_routing_backbone_key="aabbccddeeff",
    )
    installation.project_guid = UUID(WA53H10_GUID)
    session.flush()

    collection = client.get("/api/v1/installations")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["type"] == "installation"
    assert item["id"] == str(installation.id)
    assert item["attributes"]["title"] == "WA53H10"
    assert _kss_keys(item["attributes"]) == set()

    single = client.get(f"/api/v1/installations/{installation.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()


def test_get_kss_includes_kss_attributes(client: TestClient, session: Session) -> None:
    installation = persist_installation(
        session,
        title="WA53H10",
        project_start=datetime(2021, 12, 3, 11, 17, 25, 540603, tzinfo=UTC),
        schema_version="23",
        created_by="ETS6",
        tool_version="6.4.8718.0",
        bcu_key="123456",
        ip_routing_backbone_key="aabbccddeeff",
    )
    installation.project_guid = UUID(WA53H10_GUID)
    session.flush()

    collection = client.get("/api/kss/installations")
    assert collection.status_code == 200
    collection_item = collection.json()["data"][0]
    assert collection_item["attributes"]["title"] == "WA53H10"
    assert "kss:projectGuid" in collection_item["attributes"]

    response = client.get(f"/api/kss/installations/{installation.id}")
    assert response.status_code == 200
    attributes = response.json()["data"]["attributes"]
    assert attributes["title"] == "WA53H10"
    assert attributes["kss:etsId"] == WA53H10_ETS_ID
    assert attributes["kss:projectGuid"] == WA53H10_GUID
    assert "kss:installationIndex" not in attributes
    assert attributes["kss:groupAddressStyle"] == "ThreeLevel"
    assert "kss:lastImport" in attributes
    assert "kss:languageCode" not in attributes
    assert attributes["kss:projectStart"] == "2021-12-03T11:17:25.540603Z"
    assert attributes["kss:schemaVersion"] == "23"
    assert attributes["kss:createdBy"] == "ETS6"
    assert attributes["kss:toolVersion"] == "6.4.8718.0"
    assert "kss:bcuKey" not in attributes
    assert "kss:ipRoutingBackboneKey" not in attributes


def test_v1_rejects_post_and_patch(client: TestClient) -> None:
    assert client.post("/api/v1/installations", json={}).status_code == 405
    assert client.patch("/api/v1/installations", json={}).status_code == 405
    spec = client.get("/openapi.json").json()["paths"]
    assert "patch" not in spec.get("/api/v1/installations", {})
    assert "patch" in spec.get("/api/kss/installations", {})


def test_patch_unknown_format_is_422(client: TestClient) -> None:
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("notes.txt", b"not a knxproj", "text/plain")},
    )
    assert response.status_code == 422
    assert JSONAPI in response.headers["content-type"]
    errors = response.json()["errors"]
    assert errors[0]["status"] == "422"
    assert "unsupported file format" in errors[0]["detail"]
    assert ".knxproj" in errors[0]["detail"]
    assert ".ttl" in errors[0]["detail"]
    assert "planned" not in errors[0]["detail"]


def test_patch_garbage_ttl_is_422(client: TestClient) -> None:
    response = client.patch(
        "/api/kss/installations",
        files={
            "file": (
                "project.ttl",
                b"this is not turtle {{{",
                "text/turtle",
            )
        },
    )
    assert response.status_code == 422
    assert JSONAPI in response.headers["content-type"]
    error = response.json()["errors"][0]
    assert error["status"] == "422"
    assert error["title"] == "Unprocessable Entity"
    assert error["detail"]


@pytest.mark.skipif(not TEST_A1_TTL.is_file(), reason="test_A 1 .ttl missing")
def test_patch_ttl_creates_then_noop_is_201_then_204(client: TestClient) -> None:
    payload = TEST_A1_TTL.read_bytes()
    files = {
        "file": ("test_A 1 all objects #1.ttl", payload, "text/turtle"),
    }

    created = client.patch("/api/kss/installations", files=files)
    assert created.status_code == 201
    assert created.content == b""

    v1_installations = client.get("/api/v1/installations")
    assert v1_installations.status_code == 200
    v1_item = v1_installations.json()["data"][0]
    assert v1_item["attributes"]["title"] == "test_A"
    installation_id = v1_item["id"]

    kss_installations = client.get("/api/kss/installations")
    assert kss_installations.status_code == 200
    kss_item = kss_installations.json()["data"][0]
    assert kss_item["id"] == installation_id
    assert kss_item["attributes"]["kss:projectGuid"] == TEST_A1_GUID

    locations = client.get("/api/v1/locations")
    assert locations.status_code == 200
    location_items = locations.json()["data"]
    at_types = [
        type_name
        for item in location_items
        for type_name in item.get("meta", {}).get("@type", [])
    ]
    assert "loc:Room" in at_types
    assert "loc:Floor" in at_types
    assert "loc:Site" not in at_types
    assert all(item["attributes"]["title"] != "Site" for item in location_items)
    kss_locations = client.get("/api/kss/locations")
    assert "Site" not in {
        item["attributes"]["kss:etsId"] for item in kss_locations.json()["data"]
    }

    v1_devices = client.get("/api/v1/devices")
    assert v1_devices.status_code == 200
    gerat = next(
        item
        for item in v1_devices.json()["data"]
        if item["attributes"]["title"] == "Gerät 1"
    )
    assert gerat["attributes"]["individualAddress"] == "1.0.1"
    assert "assignedTrade" not in gerat["attributes"]
    assert "kss:assignedTrade" not in gerat["attributes"]

    kss_devices = client.get("/api/kss/devices")
    assert kss_devices.status_code == 200
    kss_gerat = next(
        item
        for item in kss_devices.json()["data"]
        if item["id"] == gerat["id"]
    )
    assert kss_gerat["attributes"]["kss:assignedTrade"] == "Gewerk 1"

    again = client.patch("/api/kss/installations", files=files)
    assert again.status_code == 204
    assert again.content == b""
    again_collection = client.get("/api/kss/installations")
    assert len(again_collection.json()["data"]) == 1
    assert again_collection.json()["data"][0]["id"] == installation_id


def test_patch_ets_id_conflict_is_422(
    client: TestClient, session: Session, monkeypatch
) -> None:
    persist_installation(session, ets_id=WA53H10_ETS_ID)
    session.flush()
    info = {
        "project_id": "P-FFFF",
        "name": "other",
        "last_modified": "2026-08-07T08:28:38Z",
        "group_address_style": "ThreeLevel",
        "guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "schema_version": "23",
        "installation_index": 0,
        "ets_id": WA53H10_ETS_ID,
        "completion_status": "Editing",
        "comment": None,
        "master_data_version": 1,
        "project_number": None,
        "contract_number": None,
        "project_type": None,
    }
    monkeypatch.setattr(
        "kss.api.installations.parse_knxproj",
        lambda path, password=None, language=None: {"info": info},
    )
    monkeypatch.setattr(
        "kss.api.installations.project_info",
        lambda project: project["info"],
    )
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("WA53H10.knxproj", b"stub", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert JSONAPI in response.headers["content-type"]
    assert response.json()["errors"][0]["status"] == "422"
    assert "ets id" in response.json()["errors"][0]["detail"]


def test_patch_parser_bug_is_jsonapi_500(session: Session, monkeypatch) -> None:
    def boom(path, password=None, language=None):
        del path, password, language
        raise RuntimeError("parser bug")

    monkeypatch.setattr("kss.api.installations.parse_knxproj", boom)

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.patch(
                "/api/kss/installations",
                files={
                    "file": ("WA53H10.knxproj", b"stub", "application/octet-stream")
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert JSONAPI in response.headers["content-type"]
    error = response.json()["errors"][0]
    assert error["status"] == "500"
    assert error["title"] == "Internal Server Error"
    assert "parser bug" not in error["detail"]


def test_patch_create_then_noop_is_201_then_204(
    client: TestClient, monkeypatch
) -> None:
    guid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    info = {
        "project_id": "P-FFFF",
        "name": "other",
        "last_modified": "2026-08-07T08:28:38Z",
        "group_address_style": "ThreeLevel",
        "guid": guid,
        "schema_version": "23",
        "installation_index": 0,
        "ets_id": "P-FFFF-0",
        "completion_status": "Editing",
        "comment": None,
        "master_data_version": 1,
        "project_number": None,
        "contract_number": None,
        "project_type": None,
    }
    monkeypatch.setattr(
        "kss.api.installations.parse_knxproj",
        lambda path, password=None, language=None: {"info": info},
    )
    monkeypatch.setattr(
        "kss.api.installations.project_info",
        lambda project: project["info"],
    )
    files = {"file": ("other.knxproj", b"stub", "application/octet-stream")}

    created = client.patch("/api/kss/installations", files=files)
    assert created.status_code == 201
    assert created.content == b""

    collection = client.get("/api/kss/installations")
    item = next(
        row
        for row in collection.json()["data"]
        if row["attributes"]["kss:projectGuid"] == guid
    )
    assert item["attributes"]["title"] == "other"

    again = client.patch("/api/kss/installations", files=files)
    assert again.status_code == 204
    assert again.content == b""


def test_patch_passes_accept_language_to_parser(
    client: TestClient, monkeypatch
) -> None:
    guid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    info = {
        "project_id": "P-BBBB",
        "name": "lang",
        "last_modified": "2026-08-07T08:28:38Z",
        "group_address_style": "ThreeLevel",
        "guid": guid,
        "schema_version": "23",
        "installation_index": 0,
        "ets_id": "P-BBBB-0",
        "completion_status": "Editing",
        "comment": None,
        "master_data_version": 1,
        "project_number": None,
        "contract_number": None,
        "project_type": None,
    }
    calls: list[str | None] = []

    def fake_parse(path, password=None, language=None):
        del path, password
        calls.append(language)
        return {"info": info}

    monkeypatch.setattr("kss.api.installations.parse_knxproj", fake_parse)
    monkeypatch.setattr(
        "kss.api.installations.project_info",
        lambda project: project["info"],
    )
    files = {"file": ("lang.knxproj", b"stub", "application/octet-stream")}

    with_header = client.patch(
        "/api/kss/installations",
        files=files,
        headers={"Accept-Language": "de-DE,de;q=0.9"},
    )
    assert with_header.status_code == 201
    assert calls[-1] == "de-DE"

    without_header = client.patch("/api/kss/installations", files=files)
    assert without_header.status_code == 204
    assert calls[-1] is None


def test_patch_schema_22_is_422(client: TestClient) -> None:
    payload = ETS6_FREE_KNXPROJ.read_bytes()
    response = client.patch(
        "/api/kss/installations",
        files={"file": ("ets6_free.knxproj", payload, "application/octet-stream")},
    )
    assert response.status_code == 422
    assert "below 23" in response.json()["errors"][0]["detail"]


@pytest.mark.skipif(not WA53H10_KNXPROJ.is_file(), reason="WA53H10.knxproj missing")
def test_patch_wa53h10_creates_and_is_idempotent(
    client: TestClient, session: Session, tmp_path
) -> None:
    knxproj = write_wa53h10_installation_knxproj(tmp_path / "WA53H10.knxproj")
    payload = knxproj.read_bytes()
    files = {"file": ("WA53H10.knxproj", payload, "application/octet-stream")}

    created = client.patch("/api/kss/installations", files=files)
    assert created.status_code == 201
    assert created.content == b""

    master = session.scalars(
        select(MasterData).where(
            MasterData.knx_id == "MD-1", MasterData.version == 285
        )
    ).one()
    dpst = session.scalars(
        select(MasterDatapointSubtype).where(
            MasterDatapointSubtype.master_data_id == master.id,
            MasterDatapointSubtype.knx_id == "DPST-1-1",
        )
    ).one()
    assert dpst.text == "switch"
    translation = session.scalars(
        select(MasterTranslation).where(
            MasterTranslation.master_data_id == master.id,
            MasterTranslation.knx_id == "DPST-1-1",
            MasterTranslation.language_code == "de-DE",
            MasterTranslation.attribute_name == "Text",
        )
    ).one()
    assert translation.text == "Schalten"

    collection = client.get("/api/kss/installations")
    data = next(
        item
        for item in collection.json()["data"]
        if item["attributes"]["kss:projectGuid"] == WA53H10_GUID
    )
    installation_id = data["id"]
    attributes = data["attributes"]
    assert attributes["title"] == "WA53H10"
    assert attributes["state"] == "Editing"
    assert attributes["comment"].startswith(r"{\rtf1")
    assert attributes["kss:etsId"] == WA53H10_ETS_ID
    assert attributes["kss:projectGuid"] == WA53H10_GUID
    assert "kss:installationIndex" not in attributes
    assert attributes["kss:groupAddressStyle"] == "ThreeLevel"
    assert attributes["kss:masterDataVersion"] == 285
    assert attributes["kss:projectType"] == "Family House"
    assert attributes["kss:createdBy"] == "ETS6"
    assert attributes["kss:toolVersion"].startswith("6.4")
    assert attributes["kss:schemaVersion"] == "23"
    assert attributes["kss:projectStart"].startswith("2021-12-03T11:17:25")
    assert "kss:languageCode" not in attributes
    assert "lastModified" in attributes
    assert "kss:projectType" in attributes
    assert "contractNumber" not in attributes
    assert "projectInstallationNumber" not in attributes

    v1 = client.get(f"/api/v1/installations/{installation_id}")
    assert v1.status_code == 200
    v1_attributes = v1.json()["data"]["attributes"]
    assert v1_attributes["title"] == "WA53H10"
    assert _kss_keys(v1_attributes) == set()
    assert "kss:projectType" not in v1_attributes

    locations = {
        row.ets_id: row
        for row in session.scalars(
            select(Location).where(Location.installation_id == UUID(installation_id))
        )
    }
    assert set(locations) == {"BP-1", "BP-4"}
    building = max(locations["BP-1"].versions, key=lambda item: item.last_modified)
    room = max(locations["BP-4"].versions, key=lambda item: item.last_modified)
    assert building.location_type == "Building"
    assert building.parent_location_id is None
    lines = {
        row.ets_id: row
        for row in session.scalars(
            select(Line).where(Line.installation_id == UUID(installation_id))
        )
    }
    assert set(lines) == {"L-1", "L-5"}
    assert building.default_line_id == lines["L-1"].id
    assert room.location_type == "Room"
    assert room.usage == "tag:office"
    assert room.parent_location_id == locations["BP-1"].id
    assert room.default_line_id == lines["L-5"].id
    areas = {
        row.ets_id: row
        for row in session.scalars(
            select(Area).where(Area.installation_id == UUID(installation_id))
        )
    }
    assert set(areas) == {"A-1", "A-4"}
    ip = max(areas["A-1"].versions, key=lambda item: item.last_modified)
    assert ip.address == 0
    assert ip.completion_status == "Accepted"
    segments = {
        row.ets_id: row
        for row in session.scalars(
            select(Segment).where(Segment.installation_id == UUID(installation_id))
        )
    }
    assert set(segments) == {"S-1", "S-5"}
    function = session.scalars(
        select(Function).where(Function.installation_id == UUID(installation_id))
    ).one()
    assert function.ets_id == "F-1"
    function_version = max(function.versions, key=lambda item: item.last_modified)
    assert function_version.function_type_ets_id == "FT-0"
    assert function_version.location_id == locations["BP-4"].id

    datapoint = session.scalars(
        select(Datapoint).where(Datapoint.installation_id == UUID(installation_id))
    ).one()
    assert datapoint.ets_id == "GA-1"
    datapoint_version = max(datapoint.versions, key=lambda item: item.last_modified)
    assert datapoint_version.name == "Licht schalten"
    assert datapoint_version.group_address == 256
    assert datapoint_version.datapoint_subtype_ets_id == "DPST-1-1"
    assert datapoint_version.at_type == ["knx:FunctionPoint"]
    group_range = session.scalars(
        select(GroupRange).where(GroupRange.installation_id == UUID(installation_id))
    ).one()
    assert group_range.ets_id == "GR-1"
    assert datapoint_version.group_range_id == group_range.id
    edge = session.scalars(select(FunctionDatapoint)).one()
    assert edge.function_id == function.id
    assert edge.datapoint_id == datapoint.id
    assert edge.ets_id == "GF-1"
    assert edge.role == "DR-1"
    assert edge.linked is True

    device = session.scalars(
        select(Device).where(Device.installation_id == UUID(installation_id))
    ).one()
    assert device.ets_id == "DI-1"
    device_version = max(device.versions, key=lambda item: item.last_modified)
    assert device_version.title == "UGTS_DPS1280"
    assert device_version.individual_address == "0.0.1"
    assert device_version.serial_number == "AKYmAAR/"
    assert device_version.location_id == locations["BP-4"].id
    assert device_version.segment_id == segments["S-1"].id
    assert device_version.communication_part_loaded is True
    channels = {
        row.ets_id: row
        for row in session.scalars(
            select(DeviceChannel).where(DeviceChannel.device_id == device.id)
        )
    }
    assert set(channels) == {"DI-1_CI-1", "CH-UCT"}
    supply_channel = max(
        channels["DI-1_CI-1"].versions, key=lambda item: item.last_modified
    )
    assert supply_channel.title == "Versorgung"
    assert supply_channel.description == "Netzteil"
    assert supply_channel.catalog_ref == "CH-1"
    empty_channel = max(
        channels["CH-UCT"].versions, key=lambda item: item.last_modified
    )
    assert empty_channel.catalog_ref == "CH-UCT"
    folder = session.scalars(select(DeviceFolder)).one()
    assert folder.ets_id == "PB-1"
    folder_version = max(folder.versions, key=lambda item: item.last_modified)
    assert folder_version.parent_channel_id == channels["DI-1_CI-1"].id
    comm_objects = {
        row.ets_id: row for row in session.scalars(select(CommObject)).all()
    }
    assert set(comm_objects) == {"O-1_R-1", "O-2_R-2"}
    linked_co = max(
        comm_objects["O-1_R-1"].versions, key=lambda item: item.last_modified
    )
    assert linked_co.datapoint_subtype_ets_id == "DPST-1-1"
    assert linked_co.channel_id == channels["DI-1_CI-1"].id
    unlinked_co = max(
        comm_objects["O-2_R-2"].versions, key=lambda item: item.last_modified
    )
    assert unlinked_co.read_flag is True
    assert unlinked_co.folder_id == folder.id
    co_edge = session.scalars(select(CommObjectDatapoint)).one()
    assert co_edge.comm_object_id == comm_objects["O-1_R-1"].id
    assert co_edge.datapoint_id == datapoint.id
    assert co_edge.linked is True

    pa = session.scalars(select(BusPaBinding)).one()
    assert pa.individual_address == "0.0.1"
    assert pa.device_id == device.id
    assert pa.last_downloaded == device_version.last_downloaded
    ga_binding = session.scalars(select(BusGaBinding)).one()
    assert ga_binding.group_address == 256
    assert ga_binding.device_id == device.id
    assert ga_binding.last_downloaded == device_version.last_downloaded

    trades = {
        row.ets_id: row
        for row in session.scalars(
            select(Trade).where(Trade.installation_id == UUID(installation_id))
        )
    }
    assert set(trades) == {"T-14", "T-46"}
    bus = max(trades["T-14"].versions, key=lambda item: item.last_modified)
    supply = max(trades["T-46"].versions, key=lambda item: item.last_modified)
    assert bus.name == "BUS"
    assert bus.parent_trade_id is None
    assert supply.name == "BUS_DPS1280"
    assert supply.parent_trade_id == trades["T-14"].id
    edge = session.scalars(select(TradeDevice)).one()
    assert edge.trade_id == trades["T-46"].id
    assert edge.device_id == device.id
    assert edge.linked is True

    kss_devices = client.get("/api/kss/devices")
    assert kss_devices.status_code == 200
    assert kss_devices.json()["data"][0]["attributes"]["kss:etsId"] == "DI-1"
    v1_device = client.get(f"/api/v1/devices/{device.id}")
    assert v1_device.status_code == 200
    v1_device_attrs = v1_device.json()["data"]["attributes"]
    assert "lastModified" in v1_device_attrs
    assert _kss_keys(v1_device_attrs) == set()

    kss_locations = client.get("/api/kss/locations")
    assert kss_locations.status_code == 200
    ets_ids = {
        item["attributes"]["kss:etsId"] for item in kss_locations.json()["data"]
    }
    assert {"BP-1", "BP-4"} <= ets_ids

    kss_areas = client.get("/api/kss/areas")
    assert kss_areas.status_code == 200
    area_ets = {
        item["attributes"]["kss:etsId"] for item in kss_areas.json()["data"]
    }
    assert area_ets == {"A-1", "A-4"}
    assert client.get("/api/v1/areas").status_code == 404

    kss_datapoints = client.get("/api/kss/datapoints")
    assert kss_datapoints.status_code == 200
    datapoint_ets = {
        item["attributes"]["kss:etsId"] for item in kss_datapoints.json()["data"]
    }
    assert datapoint_ets == {"O-1_R-1", "O-2_R-2"}
    v1_datapoint = client.get(f"/api/v1/datapoints/{comm_objects['O-1_R-1'].id}")
    assert v1_datapoint.status_code == 200
    v1_datapoint_attrs = v1_datapoint.json()["data"]["attributes"]
    assert v1_datapoint_attrs["title"] in {"Schalt", "O-1_R-1"}
    assert "lastModified" not in v1_datapoint_attrs
    assert _kss_keys(v1_datapoint_attrs) == set()
    assert v1_datapoint.json()["data"]["relationships"]["datapointFunctions"][
        "links"
    ]["related"] == f"/api/v1/datapoints/{comm_objects['O-1_R-1'].id}/functions"
    kss_functions = client.get("/api/kss/functions")
    assert kss_functions.status_code == 200
    assert kss_functions.json()["data"][0]["attributes"]["kss:etsId"] == "GA-1"
    v1_function = client.get(f"/api/v1/functions/{datapoint.id}")
    assert v1_function.status_code == 200
    assert v1_function.json()["data"]["attributes"]["title"] == "Licht schalten"
    assert v1_function.json()["data"]["meta"]["@type"] == ["knx:FunctionPoint"]
    assert client.get("/api/v1/group-ranges").status_code == 404
    kss_ranges = client.get("/api/kss/group-ranges")
    assert kss_ranges.status_code == 200
    assert kss_ranges.json()["data"][0]["attributes"]["kss:etsId"] == "GR-1"
    assert client.get("/api/v1/trades").status_code == 404
    kss_trades = client.get("/api/kss/trades")
    assert kss_trades.status_code == 200
    trade_ets = {
        item["attributes"]["kss:etsId"] for item in kss_trades.json()["data"]
    }
    assert trade_ets == {"T-14", "T-46"}
    assert client.get("/api/v1/channels").status_code == 404
    kss_channels = client.get("/api/kss/channels")
    assert kss_channels.status_code == 200
    channel_ets = {
        item["attributes"]["kss:etsId"] for item in kss_channels.json()["data"]
    }
    assert channel_ets == {"DI-1_CI-1", "CH-UCT"}
    kss_folders = client.get("/api/kss/folders")
    assert kss_folders.status_code == 200
    assert kss_folders.json()["data"][0]["attributes"]["kss:etsId"] == "PB-1"
    kss_application_functions = client.get("/api/kss/application-functions")
    assert kss_application_functions.status_code == 200
    assert kss_application_functions.json()["data"][0]["attributes"]["kss:etsId"] == "F-1"
    assert client.get("/api/v1/application-functions").status_code == 404
    kss_comm_objects = client.get("/api/kss/comm-objects")
    assert kss_comm_objects.status_code == 404

    again = client.patch("/api/kss/installations", files=files)
    assert again.status_code == 204
    assert again.content == b""
    assert session.scalar(select(func.count()).select_from(MasterData)) == 1
    assert session.scalar(select(func.count()).select_from(LocationVersion)) == 2
    assert session.scalar(select(func.count()).select_from(Function)) == 1
    assert session.scalar(select(func.count()).select_from(DeviceVersion)) == 1
    assert session.scalar(select(func.count()).select_from(DatapointVersion)) == 1
    assert session.scalar(select(func.count()).select_from(GroupRangeVersion)) == 1
    assert session.scalar(select(func.count()).select_from(FunctionDatapoint)) == 1
    assert session.scalar(select(func.count()).select_from(TradeVersion)) == 2
    assert session.scalar(select(func.count()).select_from(TradeDevice)) == 1
    assert session.scalar(select(func.count()).select_from(DeviceChannelVersion)) == 2
    assert session.scalar(select(func.count()).select_from(DeviceFolderVersion)) == 1
    assert session.scalar(select(func.count()).select_from(CommObjectVersion)) == 2
    assert session.scalar(select(func.count()).select_from(CommObjectDatapoint)) == 1
    assert session.scalar(select(func.count()).select_from(BusPaBinding)) == 1
    assert session.scalar(select(func.count()).select_from(BusGaBinding)) == 1
