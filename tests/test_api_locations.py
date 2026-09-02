from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import persist_function, persist_installation, persist_location

JSONAPI = "application/vnd.api+json"


def _kss_keys(attributes: dict) -> set[str]:
    return {key for key in attributes if key.startswith("kss:")}


def test_get_locations_v1_omits_kss_and_last_modified(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    building = persist_location(
        session,
        installation,
        title="00_SYS",
        ets_id="BP-1",
        location_type="Building",
        at_type=["loc:Building"],
        number="00",
        completion_status="Accepted",
    )
    room = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        location_type="Room",
        at_type=["loc:Room"],
        usage="tag:office",
        number="11",
        parent_location_id=building.id,
        description="Hobby",
        comment="Raumkommentar",
    )

    collection = client.get("/api/v1/locations")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    by_id = {item["id"]: item for item in collection.json()["data"]}
    building_item = by_id[str(building.id)]
    room_item = by_id[str(room.id)]
    assert building_item["type"] == "location"
    assert building_item["attributes"]["title"] == "00_SYS"
    assert _kss_keys(building_item["attributes"]) == set()
    assert "lastModified" not in building_item["attributes"]
    assert "state" not in building_item["attributes"]
    assert building_item["meta"]["@type"] == ["loc:Building"]
    assert "relationships" not in building_item
    assert room_item["attributes"]["description"] == "Hobby"
    assert room_item["attributes"]["comment"] == "Raumkommentar"
    assert _kss_keys(room_item["attributes"]) == set()
    assert room_item["relationships"]["parentLocation"]["data"] == {
        "type": "location",
        "id": str(building.id),
    }
    assert "childLocations" not in room_item["relationships"]
    assert "locationFunctions" not in room_item["relationships"]
    assert "locationDevices" not in room_item["relationships"]

    single = client.get(f"/api/v1/locations/{room.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()


def test_get_locations_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    location = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        location_type="Room",
        usage="tag:office",
        number="11",
        completion_status="Editing",
    )

    collection = client.get("/api/kss/locations")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "BP-4"
    assert item["attributes"]["kss:locationType"] == "Room"
    assert item["attributes"]["kss:usage"] == "tag:office"
    assert item["attributes"]["kss:number"] == "11"
    assert item["attributes"]["kss:completionStatus"] == "Editing"

    response = client.get(f"/api/kss/locations/{location.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["kss:etsId"] == "BP-4"


def test_v1_rejects_patch_on_locations(client: TestClient) -> None:
    assert client.patch("/api/v1/locations", json={}).status_code == 405
    spec = client.get("/openapi.json").json()["paths"]
    assert "patch" not in spec.get("/api/v1/locations", {})
    assert "patch" not in spec.get("/api/kss/locations", {})


def test_get_functions_v1_omits_kss(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    location = persist_location(session, installation)
    function = persist_function(
        session,
        installation,
        title="CTL_HEC_EGD",
        ets_id="F-1",
        description="Heizung",
        comment="Kommentar",
        location_id=location.id,
        at_type=["core:ApplicationFunction"],
        completion_status="Editing",
    )

    collection = client.get("/api/v1/functions")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["type"] == "function"
    assert item["id"] == str(function.id)
    assert item["attributes"]["title"] == "CTL_HEC_EGD"
    assert item["attributes"]["description"] == "Heizung"
    assert item["attributes"]["comment"] == "Kommentar"
    assert _kss_keys(item["attributes"]) == set()
    assert "lastModified" not in item["attributes"]
    assert "state" not in item["attributes"]
    assert item["meta"]["@type"] == ["core:ApplicationFunction"]
    assert item["relationships"]["functionLocation"]["data"] == {
        "type": "location",
        "id": str(location.id),
    }
    assert "functionDatapoints" not in item["relationships"]

    single = client.get(f"/api/v1/functions/{function.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()


def test_get_functions_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    function = persist_function(
        session,
        installation,
        title="CTL_HEC_EGD",
        ets_id="F-1",
        completion_status="Accepted",
    )

    collection = client.get("/api/kss/functions")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "F-1"
    assert item["attributes"]["kss:functionType"] == "FT-0"
    assert item["attributes"]["kss:completionStatus"] == "Accepted"
    assert "relationships" not in item

    response = client.get(f"/api/kss/functions/{function.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["kss:etsId"] == "F-1"
