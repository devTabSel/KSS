from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import persist_device, persist_installation, persist_trade, persist_trade_device

JSONAPI = "application/vnd.api+json"


def test_get_trades_kss_only(client: TestClient, session: Session) -> None:
    installation = persist_installation(session)
    parent = persist_trade(
        session,
        installation,
        name="BUS",
        ets_id="T-14",
        description="KNX Bus",
        completion_status="Accepted",
    )
    child = persist_trade(
        session,
        installation,
        name="BUS_DPS1280",
        ets_id="T-46",
        description="Enertex Dual Power Supply 1280",
        completion_status="Accepted",
        parent_trade_id=parent.id,
    )

    assert client.get("/api/v1/trades").status_code == 404
    spec = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/trades" not in spec
    assert "/api/kss/trades" in spec

    collection = client.get("/api/kss/trades")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    by_ets = {
        item["attributes"]["kss:etsId"]: item for item in collection.json()["data"]
    }
    assert set(by_ets) == {"T-14", "T-46"}
    assert by_ets["T-46"]["id"] == str(child.id)
    assert by_ets["T-46"]["type"] == "trade"
    assert by_ets["T-46"]["attributes"]["title"] == "BUS_DPS1280"
    assert by_ets["T-46"]["attributes"]["kss:completionStatus"] == "Accepted"
    assert "lastModified" not in by_ets["T-46"]["attributes"]
    assert by_ets["T-46"]["relationships"]["parentTrade"] == {
        "links": {"related": f"/api/kss/trades/{child.id}/parenttrade"}
    }
    assert by_ets["T-46"]["relationships"]["childTrades"] == {
        "links": {"related": f"/api/kss/trades/{child.id}/childtrades"}
    }
    assert by_ets["T-46"]["relationships"]["tradeDevices"] == {
        "links": {"related": f"/api/kss/trades/{child.id}/devices"}
    }
    assert by_ets["T-14"]["relationships"]["parentTrade"] == {
        "links": {"related": f"/api/kss/trades/{parent.id}/parenttrade"}
    }
    assert by_ets["T-14"]["relationships"]["childTrades"] == {
        "links": {"related": f"/api/kss/trades/{parent.id}/childtrades"}
    }

    single = client.get(f"/api/kss/trades/{child.id}")
    assert single.status_code == 200
    assert single.json()["data"]["attributes"]["kss:etsId"] == "T-46"

    missing = client.get("/api/kss/trades/not-a-uuid")
    assert missing.status_code == 404


def test_get_trade_parent_and_devices(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    parent = persist_trade(session, installation, name="BUS", ets_id="T-14")
    child = persist_trade(
        session,
        installation,
        name="BUS_DPS1280",
        ets_id="T-46",
        parent_trade_id=parent.id,
    )
    device = persist_device(session, installation, title="Aktor")
    persist_trade_device(session, child, device)

    parent_response = client.get(f"/api/kss/trades/{child.id}/parenttrade")
    assert parent_response.status_code == 200
    assert parent_response.json()["data"]["id"] == str(parent.id)

    root_parent = client.get(f"/api/kss/trades/{parent.id}/parenttrade")
    assert root_parent.status_code == 200
    assert root_parent.json()["data"] is None

    devices = client.get(f"/api/kss/trades/{child.id}/devices")
    assert devices.status_code == 200
    assert devices.json()["meta"]["collection"]["total"] == 1
    assert devices.json()["data"][0]["id"] == str(device.id)

    empty = client.get(f"/api/kss/trades/{parent.id}/devices")
    assert empty.json()["data"] == []
    assert empty.json()["meta"]["collection"]["total"] == 0

    children = client.get(f"/api/kss/trades/{parent.id}/childtrades")
    assert children.status_code == 200
    assert children.json()["meta"]["collection"]["total"] == 1
    assert children.json()["data"][0]["id"] == str(child.id)
    empty_children = client.get(f"/api/kss/trades/{child.id}/childtrades")
    assert empty_children.json()["data"] == []
    assert empty_children.json()["meta"]["collection"]["total"] == 0

    assert client.get("/api/v1/trades").status_code == 404
    missing = client.get("/api/kss/trades/not-a-uuid/parenttrade")
    assert missing.status_code == 404
