from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import (
    persist_channel,
    persist_comm_object,
    persist_comm_object_datapoint,
    persist_datapoint,
    persist_device,
    persist_folder,
    persist_installation,
)

JSONAPI = "application/vnd.api+json"


def test_get_channels_folders_comm_objects_kss_only(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, ets_id="DI-1")
    parent = persist_channel(
        session,
        device,
        title="Versorgung",
        ets_id="DI-1_CI-1",
        description="Netzteil",
        catalog_ref="CH-1",
    )
    child = persist_channel(
        session,
        device,
        title=None,
        ets_id="CH-ENO1",
        catalog_ref="CH-ENO1",
        parent_channel_id=parent.id,
    )
    folder = persist_folder(
        session,
        device,
        title=None,
        ets_id="PB-1",
        parent_channel_id=parent.id,
    )
    comm_object = persist_comm_object(
        session,
        device,
        name="Schalt",
        ets_id="O-1_R-1",
        number=1,
        text="Ein/Aus",
        datapoint_subtype_ets_id="DPST-1-1",
        read_flag=True,
        channel_id=parent.id,
        folder_id=folder.id,
    )

    spec = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/channels" not in spec
    assert "/api/kss/channels" in spec
    assert "/api/kss/folders" in spec
    assert "/api/kss/comm-objects" not in spec
    assert "/api/kss/group-addresses" not in spec
    assert client.get("/api/v1/channels").status_code == 404
    assert client.get("/api/v1/folders").status_code == 404
    assert client.get("/api/v1/comm-objects").status_code == 404
    assert client.get("/api/kss/comm-objects").status_code == 404

    channels = client.get("/api/kss/channels")
    assert channels.status_code == 200
    assert JSONAPI in channels.headers["content-type"]
    by_ets = {
        item["attributes"]["kss:etsId"]: item for item in channels.json()["data"]
    }
    assert set(by_ets) == {"DI-1_CI-1", "CH-ENO1"}
    assert by_ets["DI-1_CI-1"]["type"] == "channel"
    assert by_ets["DI-1_CI-1"]["id"] == str(parent.id)
    assert by_ets["DI-1_CI-1"]["attributes"]["title"] == "Versorgung"
    assert by_ets["DI-1_CI-1"]["attributes"]["description"] == "Netzteil"
    assert by_ets["DI-1_CI-1"]["attributes"]["kss:catalogRef"] == "CH-1"
    assert "lastModified" not in by_ets["DI-1_CI-1"]["attributes"]
    assert by_ets["DI-1_CI-1"]["relationships"]["device"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/device"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["parentDevice"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/parentdevice"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["parent"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/parent"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["parentChannel"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/parentchannel"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["childChannels"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/childchannels"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["childFolders"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/childfolders"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["childDatapoints"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/childdatapoints"}
    }
    assert by_ets["DI-1_CI-1"]["relationships"]["children"] == {
        "links": {"related": f"/api/kss/channels/{parent.id}/children"}
    }
    assert by_ets["CH-ENO1"]["attributes"]["title"] == "CH-ENO1"
    assert by_ets["CH-ENO1"]["relationships"]["parentChannel"] == {
        "links": {"related": f"/api/kss/channels/{child.id}/parentchannel"}
    }
    assert by_ets["CH-ENO1"]["relationships"]["childChannels"] == {
        "links": {"related": f"/api/kss/channels/{child.id}/childchannels"}
    }

    single_channel = client.get(f"/api/kss/channels/{child.id}")
    assert single_channel.status_code == 200
    assert single_channel.json()["data"]["attributes"]["kss:etsId"] == "CH-ENO1"

    folders = client.get("/api/kss/folders")
    assert folders.status_code == 200
    folder_item = folders.json()["data"][0]
    assert folder_item["type"] == "folder"
    assert folder_item["id"] == str(folder.id)
    assert folder_item["attributes"]["title"] == "PB-1"
    assert folder_item["attributes"]["kss:etsId"] == "PB-1"
    assert folder_item["relationships"]["device"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/device"}
    }
    assert folder_item["relationships"]["parentDevice"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/parentdevice"}
    }
    assert folder_item["relationships"]["parent"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/parent"}
    }
    assert folder_item["relationships"]["parentFolder"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/parentfolder"}
    }
    assert folder_item["relationships"]["childFolders"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/childfolders"}
    }
    assert folder_item["relationships"]["childDatapoints"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/childdatapoints"}
    }
    assert folder_item["relationships"]["parentChannel"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/parentchannel"}
    }
    assert folder_item["relationships"]["children"] == {
        "links": {"related": f"/api/kss/folders/{folder.id}/children"}
    }

    datapoints = client.get("/api/kss/datapoints")
    assert datapoints.status_code == 200
    dp_item = datapoints.json()["data"][0]
    assert dp_item["type"] == "datapoint"
    assert dp_item["id"] == str(comm_object.id)
    assert dp_item["attributes"]["title"] == "Schalt"
    assert dp_item["attributes"]["description"] == "Ein/Aus"
    assert dp_item["attributes"]["kss:etsId"] == "O-1_R-1"
    assert dp_item["attributes"]["kss:number"] == 1
    assert dp_item["attributes"]["kss:datapointSubtype"] == "DPST-1-1"
    assert dp_item["attributes"]["kss:readFlag"] is True
    assert "lastModified" not in dp_item["attributes"]
    assert dp_item["relationships"]["datapointDevice"] == {
        "links": {"related": f"/api/kss/datapoints/{comm_object.id}/device"}
    }
    assert dp_item["relationships"]["channel"] == {
        "links": {"related": f"/api/kss/datapoints/{comm_object.id}/channel"}
    }
    assert dp_item["relationships"]["folder"] == {
        "links": {"related": f"/api/kss/datapoints/{comm_object.id}/folder"}
    }
    assert dp_item["relationships"]["parentDevice"] == {
        "links": {"related": f"/api/kss/datapoints/{comm_object.id}/parentdevice"}
    }
    assert dp_item["relationships"]["parent"] == {
        "links": {"related": f"/api/kss/datapoints/{comm_object.id}/parent"}
    }
    assert dp_item["relationships"]["children"] == {
        "links": {"related": f"/api/kss/datapoints/{comm_object.id}/children"}
    }
    assert "groupAddresses" not in dp_item["relationships"]

    missing = client.get("/api/kss/channels/not-a-uuid")
    assert missing.status_code == 404


def test_nested_channel_folder_comm_object_relations(
    client: TestClient, session: Session
) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, ets_id="DI-1")
    parent = persist_channel(session, device, title="Versorgung", ets_id="DI-1_CI-1")
    child = persist_channel(
        session, device, title=None, ets_id="CH-ENO1", parent_channel_id=parent.id
    )
    parent_folder = persist_folder(session, device, title="Root", ets_id="PB-0")
    folder = persist_folder(
        session,
        device,
        title=None,
        ets_id="PB-1",
        parent_folder_id=parent_folder.id,
    )
    channel_folder = persist_folder(
        session, device, title=None, ets_id="PB-2", parent_channel_id=parent.id
    )
    comm_object = persist_comm_object(
        session,
        device,
        name="Schalt",
        ets_id="O-1_R-1",
        channel_id=parent.id,
        folder_id=folder.id,
    )
    datapoint = persist_datapoint(session, installation, title="Licht", ets_id="GA-1")
    persist_comm_object_datapoint(session, comm_object, datapoint)
    orphan_co = persist_comm_object(session, device, name="Frei", ets_id="O-2_R-2")

    channel_device = client.get(f"/api/kss/channels/{child.id}/device")
    assert channel_device.status_code == 200
    assert channel_device.json()["data"]["id"] == str(device.id)

    channel_parent = client.get(f"/api/kss/channels/{child.id}/parentchannel")
    assert channel_parent.json()["data"]["id"] == str(parent.id)
    root_channel_parent = client.get(f"/api/kss/channels/{parent.id}/parentchannel")
    assert root_channel_parent.json()["data"] is None
    root_tree_parent = client.get(f"/api/kss/channels/{parent.id}/parent")
    assert root_tree_parent.json()["data"]["type"] == "device"
    assert root_tree_parent.json()["data"]["id"] == str(device.id)
    assert client.get(f"/api/kss/channels/{parent.id}/parentdevice").json()["data"][
        "id"
    ] == str(device.id)
    nested_tree_parent = client.get(f"/api/kss/channels/{child.id}/parent")
    assert nested_tree_parent.json()["data"]["type"] == "channel"
    assert nested_tree_parent.json()["data"]["id"] == str(parent.id)
    assert client.get(f"/api/kss/channels/{child.id}/parentdevice").json()["data"] is None
    channel_children = client.get(f"/api/kss/channels/{parent.id}/childchannels")
    assert channel_children.json()["meta"]["collection"]["total"] == 1
    assert channel_children.json()["data"][0]["id"] == str(child.id)
    empty_channel_children = client.get(
        f"/api/kss/channels/{child.id}/childchannels"
    )
    assert empty_channel_children.json()["data"] == []
    channel_folders = client.get(f"/api/kss/channels/{parent.id}/childfolders")
    assert channel_folders.json()["meta"]["collection"]["total"] == 1
    assert channel_folders.json()["data"][0]["id"] == str(channel_folder.id)
    mixed = client.get(f"/api/kss/channels/{parent.id}/children")
    mixed_types = {item["type"] for item in mixed.json()["data"]}
    mixed_ids = {item["id"] for item in mixed.json()["data"]}
    assert mixed_types == {"channel", "folder"}
    assert mixed_ids == {str(child.id), str(channel_folder.id)}

    folder_device = client.get(f"/api/kss/folders/{folder.id}/device")
    assert folder_device.json()["data"]["id"] == str(device.id)
    nested_folder = client.get(f"/api/kss/folders/{folder.id}/parentfolder")
    assert nested_folder.json()["data"]["id"] == str(parent_folder.id)
    empty_folder_channel = client.get(f"/api/kss/folders/{folder.id}/parentchannel")
    assert empty_folder_channel.json()["data"] is None
    nested_channel = client.get(f"/api/kss/folders/{channel_folder.id}/parentchannel")
    assert nested_channel.json()["data"]["id"] == str(parent.id)
    empty_channel_folder = client.get(
        f"/api/kss/folders/{channel_folder.id}/parentfolder"
    )
    assert empty_channel_folder.json()["data"] is None
    folder_children = client.get(f"/api/kss/folders/{parent_folder.id}/childfolders")
    assert folder_children.json()["meta"]["collection"]["total"] == 1
    assert folder_children.json()["data"][0]["id"] == str(folder.id)
    empty_folder_children = client.get(
        f"/api/kss/folders/{folder.id}/childfolders"
    )
    assert empty_folder_children.json()["data"] == []
    folder_tree_parent = client.get(f"/api/kss/folders/{folder.id}/parent")
    assert folder_tree_parent.json()["data"]["type"] == "folder"
    assert folder_tree_parent.json()["data"]["id"] == str(parent_folder.id)
    assert client.get(f"/api/kss/folders/{folder.id}/parentdevice").json()["data"] is None
    channel_folder_parent = client.get(f"/api/kss/folders/{channel_folder.id}/parent")
    assert channel_folder_parent.json()["data"]["type"] == "channel"
    root_folder_parent = client.get(f"/api/kss/folders/{parent_folder.id}/parent")
    assert root_folder_parent.json()["data"]["type"] == "device"
    folder_mixed = client.get(f"/api/kss/folders/{folder.id}/children")
    assert {item["id"] for item in folder_mixed.json()["data"]} == {str(comm_object.id)}
    assert folder_mixed.json()["data"][0]["type"] == "datapoint"

    co_device = client.get(f"/api/kss/datapoints/{comm_object.id}/device")
    assert co_device.json()["data"]["id"] == str(device.id)
    assert client.get(f"/api/kss/datapoints/{comm_object.id}/parentdevice").json()[
        "data"
    ] is None
    co_tree_parent = client.get(f"/api/kss/datapoints/{comm_object.id}/parent")
    assert co_tree_parent.json()["data"]["type"] == "folder"
    assert co_tree_parent.json()["data"]["id"] == str(folder.id)
    orphan_parent_device = client.get(
        f"/api/kss/datapoints/{orphan_co.id}/parentdevice"
    )
    assert orphan_parent_device.json()["data"]["id"] == str(device.id)
    co_channel = client.get(f"/api/kss/datapoints/{comm_object.id}/channel")
    assert co_channel.json()["data"]["id"] == str(parent.id)
    co_folder = client.get(f"/api/kss/datapoints/{comm_object.id}/folder")
    assert co_folder.json()["data"]["id"] == str(folder.id)
    functions = client.get(f"/api/kss/datapoints/{comm_object.id}/functions")
    assert functions.json()["meta"]["collection"]["total"] == 1
    assert functions.json()["data"][0]["id"] == str(datapoint.id)
    assert functions.json()["data"][0]["type"] == "function"

    empty_channel = client.get(f"/api/kss/datapoints/{orphan_co.id}/channel")
    assert empty_channel.json()["data"] is None
    empty_folder = client.get(f"/api/kss/datapoints/{orphan_co.id}/folder")
    assert empty_folder.json()["data"] is None
    empty_functions = client.get(f"/api/kss/datapoints/{orphan_co.id}/functions")
    assert empty_functions.json()["data"] == []

    assert client.get("/api/v1/channels").status_code == 404
    missing = client.get("/api/kss/channels/not-a-uuid/device")
    assert missing.status_code == 404
