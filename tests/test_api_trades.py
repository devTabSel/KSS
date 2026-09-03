from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import persist_installation, persist_trade

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
    assert by_ets["T-46"]["relationships"]["parentTrade"]["data"] == {
        "type": "trade",
        "id": str(parent.id),
    }
    assert "relationships" not in by_ets["T-14"]

    single = client.get(f"/api/kss/trades/{child.id}")
    assert single.status_code == 200
    assert single.json()["data"]["attributes"]["kss:etsId"] == "T-46"

    missing = client.get("/api/kss/trades/not-a-uuid")
    assert missing.status_code == 404
