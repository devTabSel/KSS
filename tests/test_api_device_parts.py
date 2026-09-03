from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import (
    persist_channel,
    persist_comm_object,
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
    assert "/api/kss/comm-objects" in spec
    assert client.get("/api/v1/channels").status_code == 404
    assert client.get("/api/v1/folders").status_code == 404
    assert client.get("/api/v1/comm-objects").status_code == 404

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
    assert by_ets["DI-1_CI-1"]["relationships"]["device"]["data"] == {
        "type": "device",
        "id": str(device.id),
    }
    assert "parentChannel" not in by_ets["DI-1_CI-1"]["relationships"]
    assert by_ets["CH-ENO1"]["attributes"]["title"] == "CH-ENO1"
    assert by_ets["CH-ENO1"]["relationships"]["parentChannel"]["data"] == {
        "type": "channel",
        "id": str(parent.id),
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
    assert folder_item["relationships"]["parentChannel"]["data"] == {
        "type": "channel",
        "id": str(parent.id),
    }
    assert "parentFolder" not in folder_item["relationships"]

    comm_objects = client.get("/api/kss/comm-objects")
    assert comm_objects.status_code == 200
    co_item = comm_objects.json()["data"][0]
    assert co_item["type"] == "commObject"
    assert co_item["id"] == str(comm_object.id)
    assert co_item["attributes"]["title"] == "Schalt"
    assert co_item["attributes"]["description"] == "Ein/Aus"
    assert co_item["attributes"]["kss:etsId"] == "O-1_R-1"
    assert co_item["attributes"]["kss:number"] == 1
    assert co_item["attributes"]["kss:datapointSubtype"] == "DPST-1-1"
    assert co_item["attributes"]["kss:readFlag"] is True
    assert "lastModified" not in co_item["attributes"]
    assert co_item["relationships"]["channel"]["data"] == {
        "type": "channel",
        "id": str(parent.id),
    }
    assert co_item["relationships"]["folder"]["data"] == {
        "type": "folder",
        "id": str(folder.id),
    }

    missing = client.get("/api/kss/channels/not-a-uuid")
    assert missing.status_code == 404
