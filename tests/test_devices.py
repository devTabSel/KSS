from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.device import Device, DeviceChannel, DeviceVersion
from kss.models.location import Location
from kss.models.topology import Segment
from kss.services.devices import upsert_devices_from_project
from kss.services.locations import upsert_locations_from_project
from kss.services.topology import upsert_topology_from_project
from tests.helpers import persist_area_line_segment, persist_device, persist_installation
from tests.test_topology import TOPOLOGY_PROJECT

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)

DEVICE_PROJECT = {
    "topology": TOPOLOGY_PROJECT["topology"],
    "locations": {
        "00_SYS": {
            "type": "Building",
            "identifier": "P-040E-0_BP-1",
            "ets_id": "BP-1",
            "name": "00_SYS",
            "devices": [],
            "functions": [],
            "spaces": {
                "11_UGH": {
                    "type": "Room",
                    "identifier": "P-040E-0_BP-4",
                    "ets_id": "BP-4",
                    "name": "11_UGH",
                    "devices": ["0.0.1"],
                    "functions": [],
                    "spaces": {},
                }
            },
        }
    },
    "devices": {
        "0.0.1": {
            "name": "UGTS_DPS1280",
            "hardware_name": "",
            "order_number": "",
            "description": "",
            "manufacturer_name": "",
            "individual_address": "0.0.1",
            "application": None,
            "project_uid": 35,
            "communication_object_ids": [],
            "channels": {},
            "identifier": "P-040E-0_DI-1",
            "ets_id": "DI-1",
            "comment": None,
            "completion_status": "Accepted",
            "last_modified": "2026-06-11T06:43:31.8793081Z",
            "last_download": "2026-06-11T06:45:07.5603833Z",
            "serial_number": "00A62600047F",
            "communication_part_loaded": True,
            "individual_address_loaded": True,
            "application_program_loaded": True,
            "parameters_loaded": True,
            "medium_config_loaded": True,
            "product_ref": "M-00A6_H-00000026-1_P-1173",
            "hardware_program_ref": "M-00A6_H-00000026-1_HP-0026-10-39D6",
            "installation_hints": None,
            "firmware_version": None,
            "hardware_version": None,
            "bus_current": None,
            "segment_ets_id": "S-1",
        }
    },
}


def test_upsert_device_with_location_and_segment(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    upsert_topology_from_project(session, installation, DEVICE_PROJECT, FALLBACK)
    upsert_locations_from_project(session, installation, DEVICE_PROJECT, FALLBACK)
    upsert_devices_from_project(session, installation, DEVICE_PROJECT, FALLBACK)

    device = session.scalars(select(Device)).one()
    assert device.ets_id == "DI-1"
    version = max(device.versions, key=lambda item: item.last_modified)
    assert version.title == "UGTS_DPS1280"
    assert version.individual_address == "0.0.1"
    assert version.serial_number == "00A62600047F"
    assert version.communication_part_loaded is True
    assert version.product_ref == "M-00A6_H-00000026-1_P-1173"
    assert version.application_program_ref == "M-00A6_H-00000026-1_HP-0026-10-39D6"
    assert version.last_downloaded is not None
    assert version.last_downloaded.year == 2026
    location = session.scalars(select(Location).where(Location.ets_id == "BP-4")).one()
    assert version.location_id == location.id
    segment = session.scalars(select(Segment).where(Segment.ets_id == "S-1")).one()
    assert version.segment_id == segment.id
    assert session.scalar(select(func.count()).select_from(DeviceChannel)) == 0

    upsert_devices_from_project(session, installation, DEVICE_PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(DeviceVersion)) == 1


def test_missing_devices_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_area_line_segment(session, installation)
    persist_device(session, installation, ets_id="DI-99")
    upsert_devices_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(Device)) == 1
    assert session.scalars(select(Device)).one().ets_id == "DI-99"


def test_sentinel_last_download_is_not_stored(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    project = {
        "devices": {
            "1.1.1": {
                "name": "Dummy",
                "identifier": "P-040E-0_DI-9",
                "ets_id": "DI-9",
                "individual_address": "1.1.1",
                "last_download": "0001-01-01T00:00:00",
                "communication_object_ids": [],
                "channels": {},
                "hardware_name": "",
                "order_number": "",
                "description": "",
                "manufacturer_name": "",
                "application": None,
                "project_uid": None,
            }
        }
    }
    upsert_devices_from_project(session, installation, project, FALLBACK)
    version = session.scalars(select(DeviceVersion)).one()
    assert version.last_downloaded is None
    assert version.title == "Dummy"
