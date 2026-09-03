from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.bus_bindings import BusGaBinding, BusPaBinding
from kss.services.bus_bindings import upsert_bus_bindings_from_project
from tests.helpers import (
    persist_comm_object,
    persist_comm_object_datapoint,
    persist_datapoint,
    persist_device,
    persist_installation,
)

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)
DOWNLOADED = datetime(2026, 6, 11, 6, 45, 7, tzinfo=UTC)

PROJECT = {
    "devices": {
        "0.0.1": {
            "identifier": "P-040E-0_DI-1",
            "ets_id": "DI-1",
        }
    }
}


def test_upsert_pa_and_ga_when_loaded_and_downloaded(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    device = persist_device(
        session,
        installation,
        ets_id="DI-1",
        individual_address="0.0.1",
        last_downloaded=DOWNLOADED,
        individual_address_loaded=True,
        communication_part_loaded=True,
    )
    datapoint = persist_datapoint(
        session, installation, ets_id="GA-1", group_address=256
    )
    comm_object = persist_comm_object(session, device, ets_id="O-1_R-1")
    persist_comm_object_datapoint(session, comm_object, datapoint)

    upsert_bus_bindings_from_project(session, installation, PROJECT, FALLBACK)

    pa = session.scalars(select(BusPaBinding)).one()
    assert pa.installation_id == installation.id
    assert pa.individual_address == "0.0.1"
    assert pa.device_id == device.id
    assert pa.last_downloaded == DOWNLOADED

    ga = session.scalars(select(BusGaBinding)).one()
    assert ga.group_address == 256
    assert ga.device_id == device.id
    assert ga.last_downloaded == DOWNLOADED

    upsert_bus_bindings_from_project(session, installation, PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(BusPaBinding)) == 1
    assert session.scalar(select(func.count()).select_from(BusGaBinding)) == 1


def test_sentinel_or_missing_download_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_device(
        session,
        installation,
        ets_id="DI-1",
        individual_address="0.0.1",
        last_downloaded=None,
        individual_address_loaded=True,
        communication_part_loaded=True,
    )
    upsert_bus_bindings_from_project(session, installation, PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(BusPaBinding)) == 0
    assert session.scalar(select(func.count()).select_from(BusGaBinding)) == 0


def test_flags_false_skip_respective_index(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(
        session,
        installation,
        ets_id="DI-1",
        individual_address="0.0.1",
        last_downloaded=DOWNLOADED,
        individual_address_loaded=False,
        communication_part_loaded=False,
    )
    datapoint = persist_datapoint(
        session, installation, ets_id="GA-1", group_address=256
    )
    comm_object = persist_comm_object(session, device, ets_id="O-1_R-1")
    persist_comm_object_datapoint(session, comm_object, datapoint)
    upsert_bus_bindings_from_project(session, installation, PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(BusPaBinding)) == 0
    assert session.scalar(select(func.count()).select_from(BusGaBinding)) == 0


def test_unlinked_co_does_not_write_ga(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(
        session,
        installation,
        ets_id="DI-1",
        individual_address="0.0.1",
        last_downloaded=DOWNLOADED,
        individual_address_loaded=True,
        communication_part_loaded=True,
    )
    datapoint = persist_datapoint(
        session, installation, ets_id="GA-1", group_address=256
    )
    comm_object = persist_comm_object(session, device, ets_id="O-2_R-2")
    persist_comm_object_datapoint(session, comm_object, datapoint, linked=False)
    upsert_bus_bindings_from_project(session, installation, PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(BusPaBinding)) == 1
    assert session.scalar(select(func.count()).select_from(BusGaBinding)) == 0


def test_missing_devices_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_device(
        session,
        installation,
        ets_id="DI-1",
        individual_address="0.0.1",
        last_downloaded=DOWNLOADED,
        individual_address_loaded=True,
        communication_part_loaded=True,
    )
    upsert_bus_bindings_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(BusPaBinding)) == 0
