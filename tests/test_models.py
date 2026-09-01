import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kss.models.datapoint import Datapoint, DatapointVersion, GroupRange, GroupRangeVersion
from kss.models.device import (
    CommObject,
    CommObjectDatapoint,
    CommObjectVersion,
    Device,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceVersion,
)
from kss.models.installation import Datafield, Installation, InstallationVersion
from kss.models.location import FunctionDatapoint, LocationVersion
from kss.models.trade import TradeDevice
from tests.helpers import (
    at,
    persist_area_line_segment,
    persist_datapoint,
    persist_device,
    persist_function,
    persist_installation,
    persist_location,
    persist_trade,
)


def test_creates_installation_with_research_fields(session: Session) -> None:
    guid = uuid.UUID("666d92fe-6df1-445e-8c0a-a9be732a8c3f")
    installation = persist_installation(
        session,
        title="WA53H10",
        comment="rtf possible",
        contract_number="C-1",
        project_installation_number="1",
        completion_status="Undefined",
        master_data_version=278,
    )
    installation.project_guid = guid
    session.flush()
    version = session.scalars(select(InstallationVersion)).one()
    assert installation.ets_id == "P-040E-0"
    assert installation.group_address_style == "ThreeLevel"
    assert version.completion_status == "Undefined"
    assert version.master_data_version == 278
    assert version.title == "WA53H10"


def test_installation_style_rejects_unknown_value(session: Session) -> None:
    session.add(
        Installation(
            id=uuid.uuid4(),
            group_address_style="FourLevel",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_installation_completion_status_rejects_unknown(session: Session) -> None:
    installation = Installation(id=uuid.uuid4())
    session.add(installation)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="x",
            completion_status="Done",
            _since=at(0),
            _observable_since=at(1),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_installation_version_history_is_append_only(session: Session) -> None:
    installation = persist_installation(session, title="v1")
    first = session.scalars(select(InstallationVersion)).one()
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="v2",
            completion_status="Editing",
            _since=at(10),
            _observable_since=at(11),
        )
    )
    session.flush()
    session.refresh(first)
    titles = session.scalars(
        select(InstallationVersion.title).order_by(InstallationVersion._since)
    ).all()
    assert titles == ["v1", "v2"]
    assert first.title == "v1"


def test_duplicate_ets_id_in_same_installation_is_rejected(session: Session) -> None:
    installation = persist_installation(session)
    persist_device(session, installation, ets_id="DI-1")
    with pytest.raises(IntegrityError):
        persist_device(session, installation, ets_id="DI-1", title="other")


def test_same_ets_id_allowed_in_different_installations(session: Session) -> None:
    a = persist_installation(session, ets_id="P-040E-0")
    b = Installation(
        id=uuid.uuid4(),
        ets_id="P-0260-0",
        group_address_style="TwoLevel",
    )
    session.add(b)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=b.id,
            title="test_A",
            _since=at(0),
            _observable_since=at(1),
        )
    )
    persist_device(session, a, ets_id="DI-1")
    persist_device(session, b, ets_id="DI-1", title="other project")
    session.flush()


def test_location_parent_not_self_and_type_check(session: Session) -> None:
    installation = persist_installation(session)
    location = persist_location(
        session,
        installation,
        location_type="Floor",
        usage="tag:bedroom",
        completion_status="Editing",
    )
    version = session.scalars(select(LocationVersion)).one()
    assert version.location_type == "Floor"
    assert version.usage == "tag:bedroom"
    session.add(
        LocationVersion(
            location_id=location.id,
            title="loop",
            parent_location_id=location.id,
            _since=at(2),
            _observable_since=at(3),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_location_type_rejects_kim_class_name(session: Session) -> None:
    installation = persist_installation(session)
    location = persist_location(session, installation)
    session.add(
        LocationVersion(
            location_id=location.id,
            title="x",
            location_type="loc:Building",
            _since=at(2),
            _observable_since=at(3),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_location_default_line_fk(session: Session) -> None:
    installation = persist_installation(session)
    segment = persist_area_line_segment(session, installation)
    persist_location(
        session,
        installation,
        ets_id="BP-2",
        title="Raum",
        location_type="Room",
        default_line_id=segment.line_id,
    )
    version = session.scalars(
        select(LocationVersion).where(LocationVersion.title == "Raum")
    ).one()
    assert version.default_line_id == segment.line_id


def test_device_location_and_segment_are_real_fks(session: Session) -> None:
    installation = persist_installation(session)
    location = persist_location(session, installation)
    segment = persist_area_line_segment(session, installation)
    persist_device(
        session,
        installation,
        location_id=location.id,
        segment_id=segment.id,
        serial_number="00aabbccddee",
        individual_address="1.0.248",
        communication_part_loaded=True,
        completion_status="Undefined",
    )
    version = session.scalars(select(DeviceVersion)).one()
    assert version.location_id == location.id
    assert version.segment_id == segment.id


def test_device_location_fk_requires_existing_location(session: Session) -> None:
    installation = persist_installation(session)
    with pytest.raises(IntegrityError):
        persist_device(session, installation, location_id=uuid.uuid4())


def test_datapoint_address_change_keeps_identity(session: Session) -> None:
    installation = persist_installation(session)
    datapoint = persist_datapoint(session, installation, group_address=30720)
    session.add(
        DatapointVersion(
            datapoint_id=datapoint.id,
            title="Licht schalten",
            group_address=30750,
            _since=at(8),
            _observable_since=at(9),
        )
    )
    session.flush()
    versions = session.scalars(
        select(DatapointVersion)
        .where(DatapointVersion.datapoint_id == datapoint.id)
        .order_by(DatapointVersion._since)
    ).all()
    assert [row.group_address for row in versions] == [30720, 30750]
    assert datapoint.ets_id == "GA-1"


def test_group_address_out_of_range_rejected(session: Session) -> None:
    installation = persist_installation(session)
    datapoint = Datapoint(id=uuid.uuid4(), installation_id=installation.id, ets_id="GA-9")
    session.add(datapoint)
    session.flush()
    session.add(
        DatapointVersion(
            datapoint_id=datapoint.id,
            title="x",
            group_address=65536,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_group_range_and_datapoint_move(session: Session) -> None:
    installation = persist_installation(session)
    group_range = GroupRange(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id="GR-49",
    )
    session.add(group_range)
    session.flush()
    session.add(
        GroupRangeVersion(
            group_range_id=group_range.id,
            name="EGD",
            range_start=2048,
            range_end=4095,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    persist_datapoint(session, installation, group_range_id=group_range.id)
    session.flush()


def test_function_datapoint_unlink_is_new_version(session: Session) -> None:
    installation = persist_installation(session)
    location = persist_location(session, installation)
    function = persist_function(
        session,
        installation,
        location_id=location.id,
        function_type_ets_id="FT-0",
    )
    datapoint = persist_datapoint(session, installation)
    session.add(
        FunctionDatapoint(
            function_id=function.id,
            datapoint_id=datapoint.id,
            ets_id="GF-1",
            role="DR-switch",
            linked=True,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.flush()
    session.add(
        FunctionDatapoint(
            function_id=function.id,
            datapoint_id=datapoint.id,
            ets_id="GF-1",
            role="DR-switch",
            linked=False,
            _since=at(4),
            _observable_since=at(5),
        )
    )
    session.flush()
    rows = session.scalars(
        select(FunctionDatapoint).order_by(FunctionDatapoint._since)
    ).all()
    assert [row.linked for row in rows] == [True, False]


def test_function_role_accepts_free_uuid(session: Session) -> None:
    installation = persist_installation(session)
    function = persist_function(session, installation)
    datapoint = persist_datapoint(session, installation)
    role = str(uuid.uuid4())
    session.add(
        FunctionDatapoint(
            function_id=function.id,
            datapoint_id=datapoint.id,
            role=role,
            linked=True,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.flush()
    assert session.scalars(select(FunctionDatapoint)).one().role == role


def test_channel_and_comm_object_datapoint_link(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation)
    datapoint = persist_datapoint(session, installation)
    channel = DeviceChannel(id=uuid.uuid4(), device_id=device.id, ets_id="DI-1_CI-9")
    session.add(channel)
    session.flush()
    session.add(
        DeviceChannelVersion(
            channel_id=channel.id,
            title="Licht",
            catalog_ref="CH-3",
            _since=at(0),
            _observable_since=at(1),
        )
    )
    comm_object = CommObject(
        id=uuid.uuid4(),
        device_id=device.id,
        ets_id="O-1_R-1",
        channel_id=channel.id,
    )
    session.add(comm_object)
    session.flush()
    session.add(
        CommObjectVersion(
            comm_object_id=comm_object.id,
            name="Switch",
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.add(
        CommObjectDatapoint(
            comm_object_id=comm_object.id,
            datapoint_id=datapoint.id,
            linked=True,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.flush()
    assert session.scalars(select(CommObjectDatapoint)).one().linked is True


def test_trade_devices_temporal_with_device_fk(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation)
    lighting = persist_trade(session, installation, name="Gewerk 1", ets_id="T-3")
    other = persist_trade(session, installation, name="Gewerk 1", ets_id="T-4")
    session.add(
        TradeDevice(
            trade_id=lighting.id,
            device_id=device.id,
            linked=True,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.add(
        TradeDevice(
            trade_id=other.id,
            device_id=device.id,
            linked=True,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.flush()
    session.add(
        TradeDevice(
            trade_id=lighting.id,
            device_id=device.id,
            linked=False,
            _since=at(6),
            _observable_since=at(7),
        )
    )
    session.flush()
    current = session.scalars(
        select(TradeDevice)
        .where(TradeDevice.trade_id == lighting.id)
        .order_by(TradeDevice._since.desc())
        .limit(1)
    ).one()
    assert current.linked is False
    assert lighting.ets_id != other.ets_id


def test_trade_device_fk_requires_device(session: Session) -> None:
    installation = persist_installation(session)
    trade = persist_trade(session, installation)
    session.add(
        TradeDevice(
            trade_id=trade.id,
            device_id=uuid.uuid4(),
            linked=True,
            _since=at(0),
            _observable_since=at(1),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_datafield_catalog_is_current_state(session: Session) -> None:
    installation = persist_installation(session)
    session.add(
        Datafield(
            id=uuid.uuid4(),
            installation_id=installation.id,
            ets_id="DPST-1-2_F-1",
            title="bool",
            kind="enum",
            datapoint_subtype_ets_id="DPST-1-2",
            enum_value_map=[{"false": 0, "true": 1}],
        )
    )
    session.flush()
    row = session.scalars(select(Datafield)).one()
    assert row.kind == "enum"
    assert "value" not in {column.name for column in Datafield.__table__.columns}


def test_identical_since_does_not_create_second_device_version(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, title="v1", since=at(0))
    session.add(
        DeviceVersion(
            device_id=device.id,
            title="v1-again",
            _since=at(0),
            _observable_since=at(9),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
