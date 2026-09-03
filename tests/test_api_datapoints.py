from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import (
    persist_channel,
    persist_comm_object,
    persist_comm_object_datapoint,
    persist_datapoint,
    persist_device,
    persist_folder,
    persist_function,
    persist_function_datapoint,
    persist_group_range,
    persist_installation,
)

JSONAPI = "application/vnd.api+json"


def _kss_keys(attributes: dict) -> set[str]:
    return {key for key in attributes if key.startswith("kss:")}


def test_get_datapoints_v1_includes_3api_omits_kss(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, title="Aktor")
    datapoint = persist_comm_object(
        session,
        device,
        name="Schalt",
        ets_id="O-1_R-1",
        text="Ein/Aus",
        read_flag=True,
        write_flag=True,
        datapoint_subtype_ets_id="DPST-1-1",
    )

    collection = client.get("/api/v1/datapoints")
    assert collection.status_code == 200
    assert JSONAPI in collection.headers["content-type"]
    item = collection.json()["data"][0]
    assert item["type"] == "datapoint"
    assert item["id"] == str(datapoint.id)
    assert item["attributes"]["title"] == "Schalt"
    assert item["attributes"]["description"] == "Ein/Aus"
    assert item["attributes"]["readable"] is True
    assert item["attributes"]["writable"] is True
    assert "lastModified" not in item["attributes"]
    assert "value" not in item["attributes"]
    assert "timestamp" not in item["attributes"]
    assert _kss_keys(item["attributes"]) == set()
    assert "meta" not in item
    datapoint_id = str(datapoint.id)
    assert item["relationships"]["datapointFunctions"] == {
        "links": {"related": f"/api/v1/datapoints/{datapoint_id}/functions"}
    }
    assert item["relationships"]["datapointDevice"] == {
        "links": {"related": f"/api/v1/datapoints/{datapoint_id}/device"}
    }
    assert "groupRange" not in item["relationships"]
    assert "channel" not in item["relationships"]
    assert "parent" not in item["relationships"]
    assert "parentDevice" not in item["relationships"]
    assert "children" not in item["relationships"]
    assert "groupAddresses" not in item["relationships"]

    single = client.get(f"/api/v1/datapoints/{datapoint.id}")
    assert single.status_code == 200
    assert _kss_keys(single.json()["data"]["attributes"]) == set()
    assert "lastModified" not in single.json()["data"]["attributes"]


def test_get_datapoints_kss_includes_ets_id(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, title="Aktor")
    datapoint = persist_comm_object(
        session,
        device,
        name="Schalt",
        ets_id="O-1_R-1",
        number=1,
        datapoint_subtype_ets_id="DPST-1-1",
        read_flag=True,
    )

    collection = client.get("/api/kss/datapoints")
    assert collection.status_code == 200
    item = collection.json()["data"][0]
    assert item["attributes"]["kss:etsId"] == "O-1_R-1"
    assert item["attributes"]["kss:number"] == 1
    assert item["attributes"]["kss:datapointSubtype"] == "DPST-1-1"
    assert item["attributes"]["kss:readFlag"] is True
    assert item["relationships"]["channel"] == {
        "links": {"related": f"/api/kss/datapoints/{datapoint.id}/channel"}
    }
    assert item["relationships"]["folder"] == {
        "links": {"related": f"/api/kss/datapoints/{datapoint.id}/folder"}
    }
    assert item["relationships"]["parentDevice"] == {
        "links": {"related": f"/api/kss/datapoints/{datapoint.id}/parentdevice"}
    }
    assert item["relationships"]["parent"] == {
        "links": {"related": f"/api/kss/datapoints/{datapoint.id}/parent"}
    }
    assert item["relationships"]["children"] == {
        "links": {"related": f"/api/kss/datapoints/{datapoint.id}/children"}
    }
    assert "groupAddresses" not in item["relationships"]

    response = client.get(f"/api/kss/datapoints/{datapoint.id}")
    assert response.status_code == 200
    assert response.json()["data"]["attributes"]["kss:etsId"] == "O-1_R-1"


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
    assert by_ets["GR-1"]["relationships"]["parentGroupRange"] == {
        "links": {"related": f"/api/kss/group-ranges/{child.id}/parentgrouprange"}
    }
    assert by_ets["GR-1"]["relationships"]["childGroupRanges"] == {
        "links": {"related": f"/api/kss/group-ranges/{child.id}/childgroupranges"}
    }
    assert by_ets["GR-0"]["relationships"]["parentGroupRange"] == {
        "links": {"related": f"/api/kss/group-ranges/{parent.id}/parentgrouprange"}
    }
    assert by_ets["GR-0"]["relationships"]["childGroupRanges"] == {
        "links": {"related": f"/api/kss/group-ranges/{parent.id}/childgroupranges"}
    }

    single = client.get(f"/api/kss/group-ranges/{child.id}")
    assert single.status_code == 200
    assert single.json()["data"]["attributes"]["kss:etsId"] == "GR-1"

    missing = client.get("/api/kss/group-ranges/not-a-uuid")
    assert missing.status_code == 404


def test_get_datapoint_functions_and_device(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, title="Aktor")
    datapoint = persist_comm_object(session, device)
    group_address = persist_datapoint(
        session, installation, title="Licht", ets_id="GA-1"
    )
    persist_comm_object_datapoint(session, datapoint, group_address)
    application = persist_function(session, installation, title="CTL_HEC_EGD")
    persist_function_datapoint(session, application, group_address)

    functions = client.get(f"/api/v1/datapoints/{datapoint.id}/functions")
    assert functions.status_code == 200
    assert functions.json()["meta"]["collection"]["total"] == 1
    assert functions.json()["data"][0]["id"] == str(group_address.id)
    assert functions.json()["data"][0]["type"] == "function"

    device_response = client.get(f"/api/v1/datapoints/{datapoint.id}/device")
    assert device_response.status_code == 200
    assert device_response.json()["data"]["id"] == str(device.id)
    assert device_response.json()["data"]["type"] == "device"

    kss_device = client.get(f"/api/kss/datapoints/{datapoint.id}/device")
    assert kss_device.json()["data"]["id"] == str(device.id)
    parent_device = client.get(f"/api/kss/datapoints/{datapoint.id}/parentdevice")
    assert parent_device.status_code == 200
    assert parent_device.json()["data"]["id"] == str(device.id)
    tree_parent = client.get(f"/api/kss/datapoints/{datapoint.id}/parent")
    assert tree_parent.json()["data"]["type"] == "device"
    assert tree_parent.json()["data"]["id"] == str(device.id)
    empty_children = client.get(f"/api/kss/datapoints/{datapoint.id}/children")
    assert empty_children.json()["data"] == []
    assert empty_children.json()["meta"]["collection"]["total"] == 0
    assert client.get(f"/api/v1/datapoints/{datapoint.id}/parentdevice").status_code == 404
    assert client.get(f"/api/v1/datapoints/{datapoint.id}/parent").status_code == 404

    inverse = client.get(f"/api/v1/devices/{device.id}/datapoints")
    assert inverse.json()["data"][0]["id"] == str(datapoint.id)

    orphan_device = persist_device(session, installation, title="Frei", ets_id="DI-2")
    orphan = persist_comm_object(session, orphan_device, name="Frei", ets_id="O-9_R-1")
    empty_functions = client.get(f"/api/v1/datapoints/{orphan.id}/functions")
    assert empty_functions.json()["data"] == []


def test_get_function_group_range_and_group_range_parent(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    parent = persist_group_range(
        session, installation, name="Haupt", ets_id="GR-0"
    )
    child = persist_group_range(
        session,
        installation,
        name="Licht",
        ets_id="GR-1",
        parent_group_range_id=parent.id,
    )
    function = persist_datapoint(
        session, installation, title="Licht", ets_id="GA-1", group_range_id=child.id
    )

    assert client.get(f"/api/v1/functions/{function.id}/group-range").status_code == 404
    related = client.get(f"/api/kss/functions/{function.id}/group-range")
    assert related.status_code == 200
    assert related.json()["data"]["id"] == str(child.id)

    parent_response = client.get(f"/api/kss/group-ranges/{child.id}/parentgrouprange")
    assert parent_response.status_code == 200
    assert parent_response.json()["data"]["id"] == str(parent.id)

    root_parent = client.get(f"/api/kss/group-ranges/{parent.id}/parentgrouprange")
    assert root_parent.status_code == 200
    assert root_parent.json()["data"] is None

    children = client.get(f"/api/kss/group-ranges/{parent.id}/childgroupranges")
    assert children.status_code == 200
    assert children.json()["meta"]["collection"]["total"] == 1
    assert children.json()["data"][0]["id"] == str(child.id)
    empty_children = client.get(f"/api/kss/group-ranges/{child.id}/childgroupranges")
    assert empty_children.json()["data"] == []
    assert empty_children.json()["meta"]["collection"]["total"] == 0

    orphan = persist_datapoint(session, installation, title="Frei", ets_id="GA-9")
    empty_range = client.get(f"/api/kss/functions/{orphan.id}/group-range")
    assert empty_range.status_code == 200
    assert empty_range.json()["data"] is None

    missing = client.get("/api/kss/functions/not-a-uuid/group-range")
    assert missing.status_code == 404


def test_datapoint_device_vs_parent_device_and_tree_parent(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, title="Aktor")
    channel = persist_channel(session, device, title="Versorgung", ets_id="CH-1")
    folder = persist_folder(
        session, device, title="Ordner", ets_id="PB-1", parent_channel_id=channel.id
    )
    under_channel = persist_comm_object(
        session, device, name="Kanal-KO", ets_id="O-2_R-1", channel_id=channel.id
    )
    under_folder = persist_comm_object(
        session,
        device,
        name="Ordner-KO",
        ets_id="O-3_R-1",
        channel_id=channel.id,
        folder_id=folder.id,
    )

    for nested in (under_channel, under_folder):
        owned = client.get(f"/api/v1/datapoints/{nested.id}/device")
        assert owned.status_code == 200
        assert owned.json()["data"]["id"] == str(device.id)
        assert client.get(f"/api/kss/datapoints/{nested.id}/device").json()["data"][
            "id"
        ] == str(device.id)
        parent_device = client.get(f"/api/kss/datapoints/{nested.id}/parentdevice")
        assert parent_device.status_code == 200
        assert parent_device.json()["data"] is None

    channel_parent = client.get(f"/api/kss/datapoints/{under_channel.id}/parent")
    assert channel_parent.json()["data"]["type"] == "channel"
    assert channel_parent.json()["data"]["id"] == str(channel.id)

    folder_parent = client.get(f"/api/kss/datapoints/{under_folder.id}/parent")
    assert folder_parent.json()["data"]["type"] == "folder"
    assert folder_parent.json()["data"]["id"] == str(folder.id)

    channel_dps = client.get(f"/api/kss/channels/{channel.id}/childdatapoints")
    assert {item["id"] for item in channel_dps.json()["data"]} == {str(under_channel.id)}
    folder_dps = client.get(f"/api/kss/folders/{folder.id}/childdatapoints")
    assert {item["id"] for item in folder_dps.json()["data"]} == {str(under_folder.id)}

