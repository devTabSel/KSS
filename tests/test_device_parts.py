from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.device import (
    CommObject,
    CommObjectDatapoint,
    CommObjectVersion,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceFolder,
    DeviceFolderVersion,
)
from kss.services.device_parts import (
    upsert_comm_object_datapoints_from_project,
    upsert_device_parts_from_project,
)
from tests.helpers import persist_channel, persist_datapoint, persist_device, persist_installation

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)

PARTS_PROJECT = {
    "devices": {
        "0.0.1": {
            "name": "UGTS_DPS1280",
            "identifier": "P-040E-0_DI-1",
            "ets_id": "DI-1",
            "last_modified": "2026-06-11T06:43:31.8793081Z",
            "group_object_tree": {
                "channels": {
                    "DI-1_CI-1": {
                        "ets_id": "DI-1_CI-1",
                        "catalog_ref": "CH-1",
                        "title": "Versorgung",
                        "description": "Netzteil",
                        "parent_channel_ets_id": None,
                        "group_object_instances": ["O-1_R-1", "O-2_R-2"],
                    },
                    "CH-UCT": {
                        "ets_id": "CH-UCT",
                        "catalog_ref": "CH-UCT",
                        "title": None,
                        "description": None,
                        "parent_channel_ets_id": None,
                        "group_object_instances": [],
                    },
                    "CH-ENO1": {
                        "ets_id": "CH-ENO1",
                        "catalog_ref": "CH-ENO1",
                        "title": None,
                        "description": None,
                        "parent_channel_ets_id": "DI-1_CI-1",
                        "group_object_instances": [],
                    },
                },
                "folders": {
                    "PB-1": {
                        "ets_id": "PB-1",
                        "title": None,
                        "parent_folder_ets_id": None,
                        "parent_channel_ets_id": "DI-1_CI-1",
                        "group_object_instances": ["O-2_R-2"],
                    }
                },
            },
            "comm_objects": {
                "O-1_R-1": {
                    "ets_id": "O-1_R-1",
                    "number": 1,
                    "name": "Schalt",
                    "text": "Ein/Aus",
                    "datapoint_subtype_ets_id": "DPST-1-1",
                    "communication_flag": None,
                    "read_flag": None,
                    "write_flag": None,
                    "transmit_flag": None,
                    "update_flag": None,
                    "read_on_init_flag": None,
                    "priority": None,
                    "channel_ets_id": "DI-1_CI-1",
                    "folder_ets_id": None,
                    "group_address_ets_ids": ["GA-1"],
                },
                "O-2_R-2": {
                    "ets_id": "O-2_R-2",
                    "number": None,
                    "name": None,
                    "text": None,
                    "datapoint_subtype_ets_id": None,
                    "communication_flag": None,
                    "read_flag": True,
                    "write_flag": None,
                    "transmit_flag": None,
                    "update_flag": None,
                    "read_on_init_flag": None,
                    "priority": None,
                    "channel_ets_id": "DI-1_CI-1",
                    "folder_ets_id": "PB-1",
                    "group_address_ets_ids": [],
                },
            },
        }
    }
}


def test_upsert_channels_folders_comm_objects_and_ga_edge(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    device = persist_device(session, installation, ets_id="DI-1")
    datapoint = persist_datapoint(session, installation, ets_id="GA-1", group_address=256)
    upsert_device_parts_from_project(session, installation, PARTS_PROJECT, FALLBACK)
    upsert_comm_object_datapoints_from_project(
        session, installation, PARTS_PROJECT, FALLBACK
    )

    channels = {row.ets_id: row for row in session.scalars(select(DeviceChannel)).all()}
    assert set(channels) == {"DI-1_CI-1", "CH-UCT", "CH-ENO1"}
    supply = max(channels["DI-1_CI-1"].versions, key=lambda item: item.last_modified)
    assert supply.title == "Versorgung"
    assert supply.description == "Netzteil"
    assert supply.catalog_ref == "CH-1"
    assert supply.parent_channel_id is None
    nested = max(channels["CH-ENO1"].versions, key=lambda item: item.last_modified)
    assert nested.parent_channel_id == channels["DI-1_CI-1"].id
    empty = max(channels["CH-UCT"].versions, key=lambda item: item.last_modified)
    assert empty.catalog_ref == "CH-UCT"
    assert empty.description is None

    folder = session.scalars(select(DeviceFolder)).one()
    assert folder.ets_id == "PB-1"
    folder_version = max(folder.versions, key=lambda item: item.last_modified)
    assert folder_version.parent_channel_id == channels["DI-1_CI-1"].id
    assert folder_version.parent_folder_id is None

    comm_objects = {row.ets_id: row for row in session.scalars(select(CommObject)).all()}
    assert set(comm_objects) == {"O-1_R-1", "O-2_R-2"}
    linked = max(comm_objects["O-1_R-1"].versions, key=lambda item: item.last_modified)
    assert linked.name == "Schalt"
    assert linked.datapoint_subtype_ets_id == "DPST-1-1"
    assert linked.channel_id == channels["DI-1_CI-1"].id
    assert linked.folder_id is None
    unlinked = max(comm_objects["O-2_R-2"].versions, key=lambda item: item.last_modified)
    assert unlinked.read_flag is True
    assert unlinked.folder_id == folder.id

    edge = session.scalars(select(CommObjectDatapoint)).one()
    assert edge.comm_object_id == comm_objects["O-1_R-1"].id
    assert edge.datapoint_id == datapoint.id
    assert edge.linked is True

    upsert_device_parts_from_project(session, installation, PARTS_PROJECT, FALLBACK)
    upsert_comm_object_datapoints_from_project(
        session, installation, PARTS_PROJECT, FALLBACK
    )
    assert session.scalar(select(func.count()).select_from(DeviceChannelVersion)) == 3
    assert session.scalar(select(func.count()).select_from(DeviceFolderVersion)) == 1
    assert session.scalar(select(func.count()).select_from(CommObjectVersion)) == 2
    assert session.scalar(select(func.count()).select_from(CommObjectDatapoint)) == 1
    assert device.ets_id == "DI-1"


def test_missing_devices_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, ets_id="DI-1")
    persist_channel(session, device, ets_id="CH-99")
    upsert_device_parts_from_project(session, installation, {}, FALLBACK)
    upsert_comm_object_datapoints_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(DeviceChannel)) == 1
    assert session.scalars(select(DeviceChannel)).one().ets_id == "CH-99"
    assert session.scalar(select(func.count()).select_from(CommObjectDatapoint)) == 0
