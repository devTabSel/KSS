from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import persist_area_line_segment, persist_device, persist_installation, persist_location, persist_product

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
        serial_number="AKYmAAR/",
        individual_address="1.0.240",
        last_downloaded=datetime(2026, 6, 11, 6, 45, 7, tzinfo=UTC),
        completion_status="Accepted",
        communication_part_loaded=True,
        product_ref="M-00A6_H-00000026-1_P-1173",
        location_id=location.id,
        segment_id=segment.id,
    )
    persist_product(
        session,
        knx_id="M-00A6_H-00000026-1_P-1173",
        order_number="1173",
        manufacturer="MDT",
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
    assert item["attributes"]["serialNumber"] == "AKYmAAR/"
    assert item["attributes"]["individualAddress"] == "1.0.240"
    assert "lastModified" in item["attributes"]
    assert "lastDownloaded" in item["attributes"]
    assert _kss_keys(item["attributes"]) == set()
    assert "state" not in item["attributes"]
    device_id = str(device.id)
    assert item["relationships"]["deviceLocation"] == {
        "links": {"related": f"/api/v1/devices/{device_id}/location"}
    }
    assert item["relationships"]["deviceDatapoints"] == {
        "links": {"related": f"/api/v1/devices/{device_id}/datapoints"}
    }
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
        hardware_program_ref="M-00A6_H-00000026-1_HP-0026-10-39D6",
        segment_id=segment.id,
    )

    collection = client.get("/api/kss/devices")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "DI-1"
    assert item["attributes"]["kss:completionStatus"] == "Accepted"
    assert item["attributes"]["kss:communicationPartLoaded"] is True
    assert item["attributes"]["kss:productRef"] == "M-00A6_H-00000026-1_P-1173"
    assert item["attributes"]["kss:hardwareProgramRef"] == (
        "M-00A6_H-00000026-1_HP-0026-10-39D6"
    )
    assert item["relationships"]["deviceLocation"]["links"]["related"] == (
        f"/api/kss/devices/{device.id}/location"
    )
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


def test_get_device_location_and_datapoints(
    client: TestClient, session: Session
) -> None:
    from tests.helpers import persist_comm_object, persist_comm_object_datapoint, persist_datapoint

    installation = persist_installation(session)
    location = persist_location(session, installation, title="11_UGH")
    device = persist_device(
        session, installation, title="Aktor", location_id=location.id
    )
    datapoint = persist_datapoint(session, installation, title="Licht", ets_id="GA-1")
    comm_object = persist_comm_object(session, device)
    persist_comm_object_datapoint(session, comm_object, datapoint)
    other = persist_comm_object(session, device, ets_id="O-2_R-1")

    related = f"/api/v1/devices/{device.id}/location"
    assert (
        client.get(f"/api/v1/devices/{device.id}").json()["data"]["relationships"][
            "deviceLocation"
        ]["links"]["related"]
        == related
    )
    location_response = client.get(related)
    assert location_response.status_code == 200
    assert location_response.json()["data"]["id"] == str(location.id)

    datapoints = client.get(f"/api/v1/devices/{device.id}/datapoints")
    assert datapoints.status_code == 200
    body = datapoints.json()
    assert body["meta"]["collection"]["total"] == 2
    assert {item["id"] for item in body["data"]} == {
        str(comm_object.id),
        str(other.id),
    }
    inverse = client.get(f"/api/v1/datapoints/{comm_object.id}/device")
    assert inverse.json()["data"]["id"] == str(device.id)

    unlocated = persist_device(session, installation, title="Frei", ets_id="DI-2")
    empty_location = client.get(f"/api/v1/devices/{unlocated.id}/location")
    assert empty_location.status_code == 200
    assert empty_location.json()["data"] is None
