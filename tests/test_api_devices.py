from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import persist_area_line_segment, persist_device, persist_installation, persist_location

JSONAPI = "application/vnd.api+json"


def _kss_keys(attributes: dict) -> set[str]:
    return {key for key in attributes if key.startswith("kss:")}


def test_get_devices_v1_includes_3api_omits_kss(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    location = persist_location(session, installation, ets_id="BP-4")
    segment, _line_id = persist_area_line_segment(session, installation)
    device = persist_device(
        session,
        installation,
        title="UGTS_DPS1280",
        ets_id="DI-1",
        description="Netzteil",
        comment="Kommentar",
        order_number="1173",
        manufacturer="MDT",
        serial_number="00A62600047F",
        individual_address="1.0.240",
        last_downloaded=datetime(2026, 6, 11, 6, 45, 7, tzinfo=UTC),
        completion_status="Accepted",
        communication_part_loaded=True,
        product_ref="M-00A6_H-00000026-1_P-1173",
        location_id=location.id,
        segment_id=segment.id,
    )

    collection = client.get("/api/v1/devices")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    item = collection.json()["data"][0]
    assert item["type"] == "device"
    assert item["id"] == str(device.id)
    assert item["attributes"]["title"] == "UGTS_DPS1280"
    assert item["attributes"]["description"] == "Netzteil"
    assert item["attributes"]["comment"] == "Kommentar"
    assert item["attributes"]["orderNumber"] == "1173"
    assert item["attributes"]["manufacturer"] == "MDT"
    assert item["attributes"]["serialNumber"] == "00A62600047F"
    assert item["attributes"]["individualAddress"] == "1.0.240"
    assert "lastModified" in item["attributes"]
    assert "lastDownloaded" in item["attributes"]
    assert _kss_keys(item["attributes"]) == set()
    assert "state" not in item["attributes"]
    assert item["relationships"]["deviceLocation"]["data"] == {
        "type": "location",
        "id": str(location.id),
    }
    assert "deviceDatapoints" not in item["relationships"]
    assert "segment" not in item["relationships"]

    single = client.get(f"/api/v1/devices/{device.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()


def test_get_devices_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    segment, _line_id = persist_area_line_segment(session, installation)
    device = persist_device(
        session,
        installation,
        title="UGTS_DPS1280",
        ets_id="DI-1",
        completion_status="Accepted",
        communication_part_loaded=True,
        product_ref="M-00A6_H-00000026-1_P-1173",
        segment_id=segment.id,
    )

    collection = client.get("/api/kss/devices")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "DI-1"
    assert item["attributes"]["kss:completionStatus"] == "Accepted"
    assert item["attributes"]["kss:communicationPartLoaded"] is True
    assert item["attributes"]["kss:productRef"] == "M-00A6_H-00000026-1_P-1173"
    assert item["relationships"]["segment"]["data"] == {
        "type": "segment",
        "id": str(segment.id),
    }

    response = client.get(f"/api/kss/devices/{device.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["kss:etsId"] == "DI-1"


def test_get_devices_kss_includes_ttl_trade_fields(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(
        session,
        installation,
        title="Gerät 1",
        ets_id="DI-1",
        assigned_trade="Gewerk 1",
        operates_for_trade=["tag:lighting"],
    )

    v1 = client.get(f"/api/v1/devices/{device.id}")
    assert v1.status_code == 200
    v1_attributes = v1.json()["data"]["attributes"]
    assert "assignedTrade" not in v1_attributes
    assert "kss:assignedTrade" not in v1_attributes
    assert "kss:operatesForTrade" not in v1_attributes
    assert _kss_keys(v1_attributes) == set()

    kss = client.get(f"/api/kss/devices/{device.id}")
    assert kss.status_code == 200
    kss_attributes = kss.json()["data"]["attributes"]
    assert kss_attributes["kss:assignedTrade"] == "Gewerk 1"
    assert kss_attributes["kss:operatesForTrade"] == ["tag:lighting"]


def test_get_devices_kss_omits_empty_operates_for_trade(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    persist_device(
        session,
        installation,
        title="Gerät 1",
        ets_id="DI-1",
        assigned_trade="Gewerk 1",
        operates_for_trade=[],
    )

    attributes = client.get("/api/kss/devices").json()["data"][0]["attributes"]
    assert attributes["kss:assignedTrade"] == "Gewerk 1"
    assert "kss:operatesForTrade" not in attributes
