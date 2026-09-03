from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import (
    persist_comm_object,
    persist_comm_object_datapoint,
    persist_datapoint,
    persist_device,
    persist_function,
    persist_function_datapoint,
    persist_installation,
    persist_location,
)

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
    building_id = str(building.id)
    room_id = str(room.id)
    assert building_item["relationships"] == {
        "parentLocation": {
            "links": {"related": f"/api/v1/locations/{building_id}/parentlocation"}
        },
        "childLocations": {
            "links": {"related": f"/api/v1/locations/{building_id}/childlocations"}
        },
        "locationFunctions": {
            "links": {"related": f"/api/v1/locations/{building_id}/functions"}
        },
        "locationDevices": {
            "links": {"related": f"/api/v1/locations/{building_id}/devices"}
        },
    }
    assert "defaultLine" not in building_item["relationships"]
    assert room_item["attributes"]["description"] == "Hobby"
    assert room_item["attributes"]["comment"] == "Raumkommentar"
    assert _kss_keys(room_item["attributes"]) == set()
    assert room_item["relationships"]["parentLocation"] == {
        "links": {"related": f"/api/v1/locations/{room_id}/parentlocation"}
    }
    assert "data" not in room_item["relationships"]["parentLocation"]

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
    function = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        description="Schaltbefehl",
        comment="Kommentar",
        at_type=["knx:FunctionPoint"],
        completion_status="Editing",
    )

    collection = client.get("/api/v1/functions")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["type"] == "function"
    assert item["id"] == str(function.id)
    assert item["attributes"]["title"] == "Licht schalten"
    assert item["attributes"]["description"] == "Schaltbefehl"
    assert item["attributes"]["comment"] == "Kommentar"
    assert _kss_keys(item["attributes"]) == set()
    assert "lastModified" not in item["attributes"]
    assert "state" not in item["attributes"]
    assert item["meta"]["@type"] == ["knx:FunctionPoint"]
    related = f"/api/v1/functions/{function.id}/location"
    datapoints = f"/api/v1/functions/{function.id}/datapoints"
    assert item["relationships"]["functionLocation"] == {
        "links": {"related": related}
    }
    assert item["relationships"]["functionDatapoints"] == {
        "links": {"related": datapoints}
    }
    assert "data" not in item["relationships"]["functionLocation"]
    assert "groupRange" not in item["relationships"]

    single = client.get(f"/api/v1/functions/{function.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()
    assert single.json()["data"]["relationships"]["functionLocation"] == {
        "links": {"related": related}
    }
    assert single.json()["data"]["relationships"]["functionDatapoints"] == {
        "links": {"related": datapoints}
    }


def test_get_functions_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    function = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        group_address=256,
        datapoint_subtype_ets_id="DPST-1-1",
        completion_status="Accepted",
    )

    collection = client.get("/api/kss/functions")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "GA-1"
    assert item["attributes"]["kss:groupAddress"] == 256
    assert item["attributes"]["kss:datapointSubtype"] == "DPST-1-1"
    assert item["attributes"]["kss:completionStatus"] == "Accepted"
    related = f"/api/kss/functions/{function.id}/location"
    datapoints = f"/api/kss/functions/{function.id}/datapoints"
    assert item["relationships"]["functionLocation"] == {
        "links": {"related": related}
    }
    assert item["relationships"]["functionDatapoints"] == {
        "links": {"related": datapoints}
    }
    assert item["relationships"]["groupRange"] == {
        "links": {"related": f"/api/kss/functions/{function.id}/group-range"}
    }

    response = client.get(f"/api/kss/functions/{function.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["kss:etsId"] == "GA-1"
    assert response.json()["data"]["relationships"]["functionLocation"] == {
        "links": {"related": related}
    }
    assert response.json()["data"]["relationships"]["functionDatapoints"] == {
        "links": {"related": datapoints}
    }


def test_get_function_location_v1_returns_location_item(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    location = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        location_type="Room",
        at_type=["loc:Room"],
        description="Hobby",
    )
    function = persist_datapoint(session, installation, title="Licht schalten")
    persist_function_datapoint(
        session,
        persist_function(session, installation, location_id=location.id),
        function,
    )

    related = f"/api/v1/functions/{function.id}/location"
    function_item = client.get(f"/api/v1/functions/{function.id}").json()["data"]
    assert function_item["relationships"]["functionLocation"]["links"]["related"] == related

    response = client.get(related, params={"page[number]": 1, "page[size]": 1})
    assert response.status_code == 200
    assert JSONAPI in response.headers["content-type"]
    body = response.json()
    assert "collection" not in body.get("meta", {})
    item = body["data"]
    assert item["type"] == "location"
    assert item["id"] == str(location.id)
    assert item["attributes"]["title"] == "11_UGH"
    assert item["attributes"]["description"] == "Hobby"
    assert _kss_keys(item["attributes"]) == set()
    assert item["meta"]["@type"] == ["loc:Room"]


def test_get_function_location_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    location = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        location_type="Room",
    )
    function = persist_datapoint(session, installation, title="Licht schalten")
    persist_function_datapoint(
        session,
        persist_function(session, installation, location_id=location.id),
        function,
    )

    related = f"/api/kss/functions/{function.id}/location"
    function_item = client.get(f"/api/kss/functions/{function.id}").json()["data"]
    assert function_item["relationships"]["functionLocation"]["links"]["related"] == related

    response = client.get(related)
    assert response.status_code == 200
    item = response.json()["data"]
    assert item["id"] == str(location.id)
    assert item["attributes"]["kss:etsId"] == "BP-4"
    assert item["attributes"]["kss:locationType"] == "Room"


def test_get_function_location_without_assignment_returns_null_data(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    function = persist_datapoint(session, installation)

    response = client.get(f"/api/v1/functions/{function.id}/location")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] is None
    assert body["meta"]["nodata"] == "The function is not related to a location."


def test_get_function_location_missing_function_is_404(
    client: TestClient,
) -> None:
    missing = "00000000-0000-0000-0000-000000000001"
    response = client.get(f"/api/v1/functions/{missing}/location")
    assert response.status_code == 404
    assert response.json()["errors"][0]["status"] == "404"


def test_v1_rejects_patch_on_function_location(client: TestClient) -> None:
    assert client.patch(
        "/api/v1/functions/00000000-0000-0000-0000-000000000001/location",
        json={},
    ).status_code == 405
    spec = client.get("/openapi.json").json()["paths"]
    assert "patch" not in spec.get(
        "/api/v1/functions/{function_id}/location", {}
    )
    assert "/api/v1/functions/{function_id}/location" in spec
    assert "/api/kss/functions/{function_id}/location" in spec


def test_get_function_datapoints_v1_returns_collection(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    function = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        at_type=["knx:FunctionPoint"],
    )
    device = persist_device(session, installation, title="Aktor")
    linked = persist_comm_object(
        session, device, name="Schalt", ets_id="O-1_R-1", read_flag=True
    )
    unlinked = persist_comm_object(session, device, name="Alt", ets_id="O-2_R-1")
    persist_comm_object_datapoint(session, linked, function)
    persist_comm_object_datapoint(session, unlinked, function, linked=False)

    related = f"/api/v1/functions/{function.id}/datapoints"
    function_item = client.get(f"/api/v1/functions/{function.id}").json()["data"]
    assert function_item["relationships"]["functionDatapoints"]["links"][
        "related"
    ] == related

    response = client.get(related)
    assert response.status_code == 200
    assert JSONAPI in response.headers["content-type"]
    body = response.json()
    assert body["meta"]["collection"] == {"number": 0, "size": 1, "total": 1}
    item = body["data"][0]
    assert item["type"] == "datapoint"
    assert item["id"] == str(linked.id)
    assert item["attributes"]["title"] == "Schalt"
    assert item["attributes"]["readable"] is True
    assert _kss_keys(item["attributes"]) == set()
    assert "meta" not in item


def test_get_function_datapoints_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    function = persist_datapoint(
        session,
        installation,
        title="Licht schalten",
        ets_id="GA-1",
        group_address=256,
    )
    device = persist_device(session, installation, title="Aktor")
    datapoint = persist_comm_object(session, device, name="Schalt", ets_id="O-1_R-1")
    persist_comm_object_datapoint(session, datapoint, function)

    related = f"/api/kss/functions/{function.id}/datapoints"
    response = client.get(related)
    assert response.status_code == 200
    item = response.json()["data"][0]
    assert item["id"] == str(datapoint.id)
    assert item["attributes"]["kss:etsId"] == "O-1_R-1"


def test_get_function_datapoints_empty_collection(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    function = persist_datapoint(session, installation)

    response = client.get(
        f"/api/v1/functions/{function.id}/datapoints",
        params={"page[number]": 0, "page[size]": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["collection"] == {"number": 0, "size": 0, "total": 0}


def test_get_function_datapoints_missing_function_is_404(
    client: TestClient,
) -> None:
    missing = "00000000-0000-0000-0000-000000000001"
    response = client.get(f"/api/v1/functions/{missing}/datapoints")
    assert response.status_code == 404
    assert response.json()["errors"][0]["status"] == "404"


def test_v1_rejects_patch_on_function_datapoints(client: TestClient) -> None:
    assert client.patch(
        "/api/v1/functions/00000000-0000-0000-0000-000000000001/datapoints",
        json={},
    ).status_code == 405
    spec = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/functions/{function_id}/datapoints" in spec
    assert "/api/kss/functions/{function_id}/datapoints" in spec
    assert "patch" not in spec.get(
        "/api/v1/functions/{function_id}/datapoints", {}
    )


def test_get_parent_location_v1(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    building = persist_location(
        session, installation, title="00_SYS", ets_id="BP-1"
    )
    room = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        parent_location_id=building.id,
    )

    related = f"/api/v1/locations/{room.id}/parentlocation"
    item = client.get(f"/api/v1/locations/{room.id}").json()["data"]
    assert item["relationships"]["parentLocation"]["links"]["related"] == related

    response = client.get(related)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(building.id)
    assert body["data"]["attributes"]["title"] == "00_SYS"
    assert _kss_keys(body["data"]["attributes"]) == set()

    root = client.get(f"/api/v1/locations/{building.id}/parentlocation")
    assert root.status_code == 200
    assert root.json()["data"] is None
    assert root.json()["meta"]["nodata"] == "The location has no parent location."


def test_get_child_locations_and_functions_and_devices(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    building = persist_location(
        session, installation, title="00_SYS", ets_id="BP-1"
    )
    room = persist_location(
        session,
        installation,
        title="11_UGH",
        ets_id="BP-4",
        parent_location_id=building.id,
    )
    function = persist_datapoint(
        session, installation, title="Licht schalten", ets_id="GA-1"
    )
    persist_function_datapoint(
        session,
        persist_function(
            session, installation, title="CTL_HEC_EGD", location_id=room.id
        ),
        function,
    )
    device = persist_device(
        session, installation, title="Aktor", location_id=room.id
    )

    children = client.get(f"/api/v1/locations/{building.id}/childlocations")
    assert children.status_code == 200
    child_body = children.json()
    assert child_body["meta"]["collection"]["total"] == 1
    assert child_body["data"][0]["id"] == str(room.id)

    empty_children = client.get(f"/api/v1/locations/{room.id}/childlocations")
    assert empty_children.json()["meta"]["collection"] == {
        "number": 0,
        "size": 0,
        "total": 0,
    }

    functions = client.get(f"/api/v1/locations/{room.id}/functions")
    assert functions.status_code == 200
    assert functions.json()["data"][0]["id"] == str(function.id)
    assert functions.json()["data"][0]["relationships"]["functionLocation"][
        "links"
    ]["related"] == f"/api/v1/functions/{function.id}/location"

    devices = client.get(f"/api/v1/locations/{room.id}/devices")
    assert devices.status_code == 200
    assert devices.json()["data"][0]["id"] == str(device.id)

    missing = client.get(
        "/api/v1/locations/00000000-0000-0000-0000-000000000001/parentlocation"
    )
    assert missing.status_code == 404
