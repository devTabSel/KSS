from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import persist_datapoint, persist_group_range, persist_installation

JSONAPI = "application/vnd.api+json"


def _kss_keys(attributes: dict) -> set[str]:
    return {key for key in attributes if key.startswith("kss:")}


def test_get_datapoints_v1_includes_3api_omits_kss(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    group_range = persist_group_range(session, installation, ets_id="GR-1")
    datapoint = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        group_address=256,
        description="Schaltbefehl",
        comment="Kommentar",
        datapoint_subtype_ets_id="DPST-1-1",
        at_type=["knx:FunctionPoint"],
        completion_status="Accepted",
        group_range_id=group_range.id,
        readable=True,
        writable=True,
    )

    collection = client.get("/api/v1/datapoints")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    item = collection.json()["data"][0]
    assert item["type"] == "datapoint"
    assert item["id"] == str(datapoint.id)
    assert item["attributes"]["title"] == "Licht schalten"
    assert item["attributes"]["description"] == "Schaltbefehl"
    assert item["attributes"]["comment"] == "Kommentar"
    assert item["attributes"]["readable"] is True
    assert item["attributes"]["writable"] is True
    assert "lastModified" not in item["attributes"]
    assert "value" not in item["attributes"]
    assert "timestamp" not in item["attributes"]
    assert _kss_keys(item["attributes"]) == set()
    assert item["meta"]["@type"] == ["knx:FunctionPoint"]
    assert "datapointFunctions" not in item.get("relationships", {})
    assert "groupRange" not in item.get("relationships", {})

    single = client.get(f"/api/v1/datapoints/{datapoint.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()
    assert "lastModified" not in single.json()["data"]["attributes"]


def test_get_datapoints_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    group_range = persist_group_range(session, installation, ets_id="GR-1")
    datapoint = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        group_address=256,
        datapoint_subtype_ets_id="DPST-1-1",
        completion_status="Accepted",
        group_range_id=group_range.id,
    )

    collection = client.get("/api/kss/datapoints")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "GA-1"
    assert item["attributes"]["kss:groupAddress"] == 256
    assert item["attributes"]["kss:datapointSubtype"] == "DPST-1-1"
    assert item["attributes"]["kss:completionStatus"] == "Accepted"
    assert item["relationships"]["groupRange"]["data"] == {
        "type": "groupRange",
        "id": str(group_range.id),
    }

    response = client.get(f"/api/kss/datapoints/{datapoint.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["kss:etsId"] == "GA-1"


def test_get_group_ranges_kss_only(client: TestClient, session: Session) -> None:
    installation = persist_installation(session)
    parent = persist_group_range(
        session, installation, name="Haupt", ets_id="GR-0", range_start=0, range_end=2047
    )
    child = persist_group_range(
        session,
        installation,
        name="Licht",
        ets_id="GR-1",
        range_start=256,
        range_end=511,
        parent_group_range_id=parent.id,
    )

    assert client.get("/api/v1/group-ranges").status_code == 404
    spec = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/group-ranges" not in spec
    assert "/api/kss/group-ranges" in spec

    collection = client.get("/api/kss/group-ranges")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    by_ets = {
        item["attributes"]["kss:etsId"]: item for item in collection.json()["data"]
    }
    assert set(by_ets) == {"GR-0", "GR-1"}
    assert by_ets["GR-1"]["id"] == str(child.id)
    assert by_ets["GR-1"]["attributes"]["title"] == "Licht"
    assert by_ets["GR-1"]["attributes"]["kss:rangeStart"] == 256
    assert "lastModified" not in by_ets["GR-1"]["attributes"]
    assert by_ets["GR-1"]["relationships"]["parentGroupRange"]["data"] == {
        "type": "groupRange",
        "id": str(parent.id),
    }
    assert "relationships" not in by_ets["GR-0"]

    single = client.get(f"/api/kss/group-ranges/{child.id}")
    assert single.status_code == 200
    assert single.json()["data"]["attributes"]["kss:etsId"] == "GR-1"

    missing = client.get("/api/kss/group-ranges/not-a-uuid")
    assert missing.status_code == 404
