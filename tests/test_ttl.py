from datetime import UTC, datetime
from pathlib import Path

from rdflib import URIRef
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from kss.models.datapoint import Datapoint, DatapointVersion
from kss.models.device import Device, DeviceVersion
from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionVersion, Location, LocationVersion
from kss.models.master import MasterHardware, MasterProduct
from kss.models.trade import Trade
from kss.services.installations import upsert_installation_from_info
from kss.services.ttl import TtlImportError, ingest_ttl, parse_ttl
from tests.wa53h10 import WA53H10_ETS_ID, WA53H10_GUID, WA53H10_INFO

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
TEST_A1_TTL = WORKSPACE_ROOT / "research" / "test_A 1 all objects #1.ttl"
WA53H10_TTL = WORKSPACE_ROOT / "research" / "WA53H10.ttl"
TEST_A1_GUID = "d0eb6c35-7a1e-41dd-8832-105ae1964af1"


def _import_clock() -> datetime:
    return datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _current_location(session: Session, ets_id: str) -> tuple[Location, LocationVersion]:
    location = session.scalars(
        select(Location)
        .where(Location.ets_id == ets_id)
        .options(selectinload(Location.versions))
    ).one()
    return location, max(location.versions, key=lambda item: item.last_modified)


def _current_device(session: Session, ets_id: str) -> tuple[Device, DeviceVersion]:
    device = session.scalars(
        select(Device)
        .where(Device.ets_id == ets_id)
        .options(selectinload(Device.versions))
    ).one()
    return device, max(device.versions, key=lambda item: item.last_modified)


def _current_function(session: Session, ets_id: str) -> tuple[Function, FunctionVersion]:
    function = session.scalars(
        select(Function)
        .where(Function.ets_id == ets_id)
        .options(selectinload(Function.versions))
    ).one()
    return function, max(function.versions, key=lambda item: item.last_modified)


def _current_datapoint(
    session: Session, ets_id: str
) -> tuple[Datapoint, DatapointVersion]:
    datapoint = session.scalars(
        select(Datapoint)
        .where(Datapoint.ets_id == ets_id)
        .options(selectinload(Datapoint.versions))
    ).one()
    return datapoint, max(datapoint.versions, key=lambda item: item.last_modified)


def test_ingest_test_a1_all_objects(session: Session) -> None:
    clock = _import_clock()
    result = ingest_ttl(session, TEST_A1_TTL, import_clock=clock)
    assert result.created is True
    assert result.installation.ets_id == "P-0260-0"
    assert str(result.installation.project_guid) == TEST_A1_GUID
    assert result.version.title == "test_A"
    assert result.installation.last_import == clock

    ets_ids = {row.ets_id for row in session.scalars(select(Location)).all()}
    assert "Site" not in ets_ids
    floor, floor_version = _current_location(session, "BP-3")
    room, room_version = _current_location(session, "BP-4")
    assert floor_version.location_type == "Floor"
    assert room_version.location_type == "Room"
    assert room_version.parent_location_id == floor.id
    assert floor_version.parent_location_id is not None

    _device, device_version = _current_device(session, "DI-1")
    assert device_version.title == "Gerät 1"
    assert device_version.assigned_trade == "Gewerk 1"
    assert device_version.individual_address == "1.0.1"
    assert device_version.last_downloaded is None
    assert device_version.location_id == room.id
    assert device_version.product_ref == "M-00FA_H-0xA012-1_P-OpenKnxRaumController"
    assert device_version.hardware_program_ref is None
    assert not hasattr(device_version, "order_number")
    assert not hasattr(device_version, "manufacturer")
    product = session.scalars(
        select(MasterProduct).where(MasterProduct.knx_id == device_version.product_ref)
    ).one()
    assert product.order_number == "OpenKnxRaumController"
    assert product.manufacturer == "KNX Association"
    assert product.text == "OpenKNX: RaumController"
    assert product.hardware_knx_id == "M-00FA_H-0xA012-1"
    hardware = session.scalars(
        select(MasterHardware).where(MasterHardware.knx_id == product.hardware_knx_id)
    ).one()
    assert hardware.manufacturer_knx_id == "M-00FA"

    _function, function_version = _current_function(session, "F-1")
    assert function_version.title == "Funktion 1"
    assert function_version.location_id == room.id
    assert function_version.function_type_ets_id == "FT-0"
    assert "core:ApplicationFunction" in (function_version.at_type or [])

    _datapoint, datapoint_version = _current_datapoint(session, "GA-1")
    assert datapoint_version.group_address == 1
    assert "knx:FunctionPoint" in (datapoint_version.at_type or [])

    dp_ets_ids = [row.ets_id for row in session.scalars(select(Datapoint)).all()]
    assert dp_ets_ids
    assert all(ets_id.startswith("GA-") for ets_id in dp_ets_ids)
    assert not any("_O-" in ets_id for ets_id in dp_ets_ids)
    assert session.scalar(select(func.count()).select_from(Trade)) == 0


def test_identical_reimport_updates_last_import_without_versioning(
    session: Session,
) -> None:
    first_clock = _import_clock()
    first = ingest_ttl(session, TEST_A1_TTL, import_clock=first_clock)
    second_clock = datetime(2026, 9, 1, 13, 0, tzinfo=UTC)
    second = ingest_ttl(session, TEST_A1_TTL, import_clock=second_clock)
    assert second.created is False
    assert second.versioned is False
    assert second.installation.id == first.installation.id
    assert second.installation.last_import == second_clock
    assert session.scalar(select(func.count()).select_from(InstallationVersion)) == 1
    assert session.scalar(select(func.count()).select_from(DeviceVersion)) == 1
    assert session.scalar(select(func.count()).select_from(LocationVersion)) == 4
    assert session.scalar(select(func.count()).select_from(MasterProduct)) == 1
    assert session.scalar(select(func.count()).select_from(MasterHardware)) == 1


def test_join_knxproj_info_then_wa53h10_ttl(session: Session) -> None:
    knxproj = upsert_installation_from_info(
        session, dict(WA53H10_INFO), import_clock=_import_clock()
    )
    ttl_clock = datetime(2026, 9, 1, 13, 0, tzinfo=UTC)
    result = ingest_ttl(session, WA53H10_TTL, import_clock=ttl_clock)
    assert result.installation.id == knxproj.installation.id
    assert str(result.installation.project_guid) == WA53H10_GUID
    assert result.installation.ets_id == WA53H10_ETS_ID
    assert result.installation.last_import == ttl_clock

    installation = session.get(
        Installation,
        result.installation.id,
        options=(selectinload(Installation.versions),),
    )
    assert installation is not None
    current = max(installation.versions, key=lambda item: item.last_modified)
    assert current.group_address_style == "ThreeLevel"
    assert current.title == "WA53H10"
    assert current.completion_status == "Editing"

    _device, device_version = _current_device(session, "DI-1")
    assert device_version.assigned_trade == "BUS_DPS1280"
    assert device_version.serial_number == "AKYmAAR/"
    assert not device_version.serial_number.startswith("$")
    assert device_version.product_ref == "M-00A6_H-00000026-1_P-1173"
    assert device_version.hardware_program_ref is None
    product = session.scalars(
        select(MasterProduct).where(MasterProduct.knx_id == device_version.product_ref)
    ).one()
    assert product.order_number == "1173"
    assert product.manufacturer == "Enertex Bayern GmbH"
    assert product.text == "Enertex KNX Dual PowerSupply 1280"
    assert product.hardware_knx_id == "M-00A6_H-00000026-1"
    hardware = session.scalars(
        select(MasterHardware).where(MasterHardware.knx_id == product.hardware_knx_id)
    ).one()
    assert hardware.manufacturer_knx_id == "M-00A6"

    building, building_version = _current_location(session, "BP-1")
    assert building_version.location_type == "Building"
    assert "loc:Building" in (building_version.at_type or [])
    assert building_version.parent_location_id is None
    assert "Site" not in {row.ets_id for row in session.scalars(select(Location)).all()}


def test_wa53h10_ttl_only_installation_and_building(session: Session) -> None:
    result = ingest_ttl(session, WA53H10_TTL, import_clock=_import_clock())
    assert result.created is True
    assert result.version.title == "WA53H10"
    assert result.version.completion_status == "Editing"
    assert result.installation.ets_id == "P-040E-0"
    assert str(result.installation.project_guid) == WA53H10_GUID
    _building, building_version = _current_location(session, "BP-1")
    assert building_version.location_type == "Building"
    assert "loc:Building" in (building_version.at_type or [])
    assert "Site" not in {row.ets_id for row in session.scalars(select(Location)).all()}


def test_garbage_file_raises_ttl_import_error(session: Session, tmp_path: Path) -> None:
    garbage = tmp_path / "garbage.ttl"
    garbage.write_text("this is not turtle {{{", encoding="utf-8")
    with pytest.raises(TtlImportError):
        ingest_ttl(session, garbage, import_clock=_import_clock())


def test_parse_truncates_before_ontology() -> None:
    parsed = parse_ttl(TEST_A1_TTL)
    available = URIRef("http://purl.org/dc/terms/available")
    assert not list(parsed.graph.predicate_objects(available))
    assert parsed.installation_ets_id == "P-0260-0"
    assert "Site" in parsed.individuals
    assert "BP-3" in parsed.individuals


def test_product_catalog_insert_if_missing_does_not_overwrite(session: Session) -> None:
    ingest_ttl(session, TEST_A1_TTL, import_clock=_import_clock())
    product = session.scalars(select(MasterProduct)).one()
    product.manufacturer = "CHANGED"
    product.order_number = "CHANGED"
    product.text = "CHANGED"
    session.flush()
    ingest_ttl(session, TEST_A1_TTL, import_clock=datetime(2026, 9, 1, 13, 0, tzinfo=UTC))
    again = session.scalars(select(MasterProduct)).one()
    assert again.manufacturer == "CHANGED"
    assert again.order_number == "CHANGED"
    assert again.text == "CHANGED"
    assert session.scalar(select(func.count()).select_from(MasterProduct)) == 1
    assert session.scalar(select(func.count()).select_from(MasterHardware)) == 1


def test_product_catalog_skips_non_hardware_product_id(
    session: Session, tmp_path: Path
) -> None:
    ttl = tmp_path / "skip_catalog.ttl"
    ttl.write_text(
        """\
@prefix prj: <http://iot.knx.org/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa#> .
@prefix core: <http://schema.knx.org/2023/en50090-6-2/core#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

prj:P-0001-0 dct:title "Skip catalog";
             a core:Installation,
               owl:NamedIndividual.
prj:DI-1 dct:title "Gerät";
         core:hasProduct prj:NotACatalogProduct;
         a core:Device,
           owl:NamedIndividual.
prj:NotACatalogProduct dct:title "Loose product";
                       core:manufacturer "Acme";
                       core:orderNumber "X";
                       a core:Product,
                         owl:NamedIndividual.
""",
        encoding="utf-8",
    )
    ingest_ttl(session, ttl, import_clock=_import_clock())
    _device, device_version = _current_device(session, "DI-1")
    assert device_version.product_ref == "NotACatalogProduct"
    assert session.scalar(select(func.count()).select_from(MasterProduct)) == 0
    assert session.scalar(select(func.count()).select_from(MasterHardware)) == 0


def test_product_catalog_manufacturer_prefix_falls_back(
    session: Session, tmp_path: Path
) -> None:
    ttl = tmp_path / "fallback_mfg.ttl"
    ttl.write_text(
        """\
@prefix prj: <http://iot.knx.org/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb#> .
@prefix core: <http://schema.knx.org/2023/en50090-6-2/core#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

prj:P-0002-0 dct:title "Fallback manufacturer";
             a core:Installation,
               owl:NamedIndividual.
prj:DI-1 dct:title "Gerät";
         core:hasProduct prj:M-ZZZZ_H-1_P-1;
         a core:Device,
           owl:NamedIndividual.
prj:M-ZZZZ_H-1_P-1 dct:title "Odd product";
                   core:manufacturer "OddCo";
                   core:orderNumber "1";
                   a core:Product,
                     owl:NamedIndividual.
""",
        encoding="utf-8",
    )
    ingest_ttl(session, ttl, import_clock=_import_clock())
    product = session.scalars(select(MasterProduct)).one()
    assert product.knx_id == "M-ZZZZ_H-1_P-1"
    assert product.hardware_knx_id == "M-ZZZZ_H-1"
    hardware = session.scalars(select(MasterHardware)).one()
    assert hardware.manufacturer_knx_id == "M-0000"

