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
    DeviceFolder,
    DeviceFolderVersion,
    DeviceVersion,
)
from kss.models.installation import Installation, InstallationVersion
from kss.models.master import Datafield, MasterData, MasterProjectType
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
        project_type="Family House",
    )
    installation.project_guid = guid
    session.flush()
    version = session.scalars(select(InstallationVersion)).one()
    assert installation.ets_id == "P-040E-0"
    assert version.group_address_style == "ThreeLevel"
    assert version.completion_status == "Undefined"
    assert version.master_data_version == 278
    assert version.title == "WA53H10"
    assert version.project_type == "Family House"
    assert version.comment == "rtf possible"
    assert version.contract_number == "C-1"
    assert version.project_installation_number == "1"


def test_installation_style_rejects_unknown_value(session: Session) -> None:
    installation = Installation(
        id=uuid.uuid4(),
        ets_id="P-STYLE-0",
        project_guid=uuid.uuid4(),
        last_import=at(1),
    )
    session.add(installation)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="x",
            group_address_style="FourLevel",
            last_modified=at(0),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_installation_completion_status_rejects_unknown(session: Session) -> None:
    installation = Installation(
        id=uuid.uuid4(),
        ets_id="P-CS-0",
        project_guid=uuid.uuid4(),
        last_import=at(1),
    )
    session.add(installation)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="x",
            completion_status="Done",
            last_modified=at(0),
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
            last_modified=at(10),
        )
    )
    session.flush()
    session.refresh(first)
    titles = session.scalars(
        select(InstallationVersion.title).order_by(InstallationVersion.last_modified)
    ).all()
    assert titles == ["v1", "v2"]
    assert first.title == "v1"


def test_installation_project_type_rejects_unknown(session: Session) -> None:
    installation = Installation(
        id=uuid.uuid4(),
        ets_id="P-PT-0",
        project_guid=uuid.uuid4(),
        last_import=at(1),
    )
    session.add(installation)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title="x",
            project_type="Familienhaus",
            last_modified=at(0),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_installation_project_type_is_nullable(session: Session) -> None:
    installation = persist_installation(session, title="no type")
    version = session.scalars(select(InstallationVersion)).one()
    assert version.project_type is None
    assert installation.ets_id == "P-040E-0"


def test_master_project_type_stores_localized_labels(session: Session) -> None:
    installation = persist_installation(session, project_type="Family House")
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Family House",
            language_code="en-US",
            name="Family House",
        )
    )
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Family House",
            language_code="de-DE",
            name="Familienhaus",
        )
    )
    session.flush()
    rows = session.scalars(
        select(MasterProjectType).order_by(MasterProjectType.language_code)
    ).all()
    assert [(row.language_code, row.name) for row in rows] == [
        ("de-DE", "Familienhaus"),
        ("en-US", "Family House"),
    ]
    assert {row.ets_id for row in rows} == {"Family House"}


def test_master_project_type_rejects_duplicate_language(session: Session) -> None:
    installation = persist_installation(session)
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Family House",
            language_code="de-DE",
            name="Familienhaus",
        )
    )
    session.flush()
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Family House",
            language_code="de-DE",
            name="Einfamilienhaus",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_master_project_type_rejects_unknown_ets_id(session: Session) -> None:
    installation = persist_installation(session)
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Familienhaus",
            language_code="de-DE",
            name="Familienhaus",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_master_project_type_rejects_blank_name(session: Session) -> None:
    installation = persist_installation(session)
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Family House",
            language_code="de-DE",
            name="   ",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_master_project_type_rejects_short_language_code(session: Session) -> None:
    installation = persist_installation(session)
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Family House",
            language_code="x",
            name="Family House",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_master_project_type_is_global_without_installation(session: Session) -> None:
    session.add(
        MasterProjectType(
            id=uuid.uuid4(),
            ets_id="Other (Other)",
            language_code="en",
            name="Other (Other)",
        )
    )
    session.flush()
    row = session.scalars(select(MasterProjectType)).one()
    assert row.ets_id == "Other (Other)"
    assert row.language_code == "en"


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
        project_guid=uuid.uuid4(),
        last_import=at(1),
    )
    session.add(b)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=b.id,
            title="test_A",
            group_address_style="TwoLevel",
            last_modified=at(0),
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
            last_modified=at(2),
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
            last_modified=at(2),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_location_default_line_fk(session: Session) -> None:
    installation = persist_installation(session)
    segment, line_id = persist_area_line_segment(session, installation)
    persist_location(
        session,
        installation,
        ets_id="BP-2",
        title="Raum",
        location_type="Room",
        default_line_id=line_id,
    )
    version = session.scalars(
        select(LocationVersion).where(LocationVersion.title == "Raum")
    ).one()
    assert version.default_line_id == line_id


def test_device_location_and_segment_are_real_fks(session: Session) -> None:
    installation = persist_installation(session)
    location = persist_location(session, installation)
    segment, _line_id = persist_area_line_segment(session, installation)
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
            name="Licht schalten",
            group_address=30750,
            last_modified=at(8),
        )
    )
    session.flush()
    versions = session.scalars(
        select(DatapointVersion)
        .where(DatapointVersion.datapoint_id == datapoint.id)
        .order_by(DatapointVersion.last_modified)
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
            name="x",
            group_address=65536,
            last_modified=at(0),
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
            last_modified=at(0),
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
            last_modified=at(0),
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
            last_modified=at(4),
        )
    )
    session.flush()
    rows = session.scalars(
        select(FunctionDatapoint).order_by(FunctionDatapoint.last_modified)
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
            last_modified=at(0),
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
            description="UGH SD Büro Studio über Tisch",
            catalog_ref="CH-3",
            last_modified=at(0),
        )
    )
    comm_object = CommObject(
        id=uuid.uuid4(),
        device_id=device.id,
        ets_id="O-1_R-1",
    )
    session.add(comm_object)
    session.flush()
    session.add(
        CommObjectVersion(
            comm_object_id=comm_object.id,
            name="Switch",
            channel_id=channel.id,
            last_modified=at(0),
        )
    )
    session.add(
        CommObjectDatapoint(
            comm_object_id=comm_object.id,
            datapoint_id=datapoint.id,
            linked=True,
            last_modified=at(0),
        )
    )
    session.flush()
    channel_version = session.scalars(select(DeviceChannelVersion)).one()
    assert channel_version.description == "UGH SD Büro Studio über Tisch"
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
            last_modified=at(0),
        )
    )
    session.add(
        TradeDevice(
            trade_id=other.id,
            device_id=device.id,
            linked=True,
            last_modified=at(0),
        )
    )
    session.flush()
    session.add(
        TradeDevice(
            trade_id=lighting.id,
            device_id=device.id,
            linked=False,
            last_modified=at(6),
        )
    )
    session.flush()
    current = session.scalars(
        select(TradeDevice)
        .where(TradeDevice.trade_id == lighting.id)
        .order_by(TradeDevice.last_modified.desc())
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
            last_modified=at(0),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_datafield_catalog_is_current_state(session: Session) -> None:
    snapshot = MasterData(id=uuid.uuid4(), knx_id="MD-1", version=1)
    session.add(snapshot)
    session.flush()
    session.add(
        Datafield(
            id=uuid.uuid4(),
            master_data_id=snapshot.id,
            knx_id="DPST-1-2_F-1",
            title="bool",
            kind="enum",
            datapoint_subtype_knx_id="DPST-1-2",
            enum_value_map=[{"false": 0, "true": 1}],
        )
    )
    session.flush()
    row = session.scalars(select(Datafield)).one()
    assert row.kind == "enum"
    assert row.knx_id == "DPST-1-2_F-1"
    assert "value" not in {column.name for column in Datafield.__table__.columns}


def test_folder_parent_may_be_device_folder_or_channel(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation)
    channel = DeviceChannel(id=uuid.uuid4(), device_id=device.id, ets_id="CH-Basic")
    parent_folder = DeviceFolder(id=uuid.uuid4(), device_id=device.id, ets_id="PB-13")
    child_folder = DeviceFolder(id=uuid.uuid4(), device_id=device.id, ets_id="PB-14")
    device_root = DeviceFolder(id=uuid.uuid4(), device_id=device.id, ets_id="PB-99")
    session.add_all([channel, parent_folder, child_folder, device_root])
    session.flush()
    session.add(
        DeviceChannelVersion(
            channel_id=channel.id,
            title="Zutrittskontrolle",
            catalog_ref="CH-Basic",
            last_modified=at(0),
        )
    )
    session.add(
        DeviceFolderVersion(
            folder_id=device_root.id,
            title="unter Gerät",
            last_modified=at(0),
        )
    )
    session.add(
        DeviceFolderVersion(
            folder_id=parent_folder.id,
            title="Allgemein",
            parent_channel_id=channel.id,
            last_modified=at(0),
        )
    )
    session.add(
        DeviceFolderVersion(
            folder_id=child_folder.id,
            title="Fingerprint-Scanner",
            parent_folder_id=parent_folder.id,
            last_modified=at(0),
        )
    )
    session.flush()
    under_device = session.scalars(
        select(DeviceFolderVersion).where(DeviceFolderVersion.folder_id == device_root.id)
    ).one()
    under_channel = session.scalars(
        select(DeviceFolderVersion).where(DeviceFolderVersion.folder_id == parent_folder.id)
    ).one()
    under_folder = session.scalars(
        select(DeviceFolderVersion).where(DeviceFolderVersion.folder_id == child_folder.id)
    ).one()
    assert under_device.parent_folder_id is None
    assert under_device.parent_channel_id is None
    assert under_channel.parent_channel_id == channel.id
    assert under_channel.parent_folder_id is None
    assert under_folder.parent_folder_id == parent_folder.id
    assert under_folder.parent_channel_id is None


def test_folder_rejects_both_parents(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation)
    channel = DeviceChannel(id=uuid.uuid4(), device_id=device.id, ets_id="CH-Basic")
    parent_folder = DeviceFolder(id=uuid.uuid4(), device_id=device.id, ets_id="PB-13")
    child_folder = DeviceFolder(id=uuid.uuid4(), device_id=device.id, ets_id="PB-14")
    session.add_all([channel, parent_folder, child_folder])
    session.flush()
    session.add(
        DeviceFolderVersion(
            folder_id=child_folder.id,
            title="illegal",
            parent_folder_id=parent_folder.id,
            parent_channel_id=channel.id,
            last_modified=at(0),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_channel_without_channel_instance_is_insertable(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, ets_id="DI-153")
    channel = DeviceChannel(id=uuid.uuid4(), device_id=device.id, ets_id="CH-UCT")
    session.add(channel)
    session.flush()
    session.add(
        DeviceChannelVersion(
            channel_id=channel.id,
            title="Konfigurationstransfer",
            catalog_ref="CH-UCT",
            last_modified=at(0),
        )
    )
    session.flush()
    row = session.scalars(select(DeviceChannel)).one()
    version = session.scalars(select(DeviceChannelVersion)).one()
    assert row.ets_id == "CH-UCT"
    assert version.catalog_ref == "CH-UCT"
    assert version.parent_channel_id is None
    assert version.description is None


def test_nested_channel_parent_and_not_self(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, ets_id="DI-88")
    parent = DeviceChannel(id=uuid.uuid4(), device_id=device.id, ets_id="CH-1")
    child = DeviceChannel(id=uuid.uuid4(), device_id=device.id, ets_id="CH-ENO1")
    session.add_all([parent, child])
    session.flush()
    session.add(
        DeviceChannelVersion(
            channel_id=parent.id,
            catalog_ref="CH-1",
            last_modified=at(0),
        )
    )
    session.add(
        DeviceChannelVersion(
            channel_id=child.id,
            catalog_ref="CH-ENO1",
            parent_channel_id=parent.id,
            last_modified=at(0),
        )
    )
    session.flush()
    nested = session.scalars(
        select(DeviceChannelVersion).where(DeviceChannelVersion.channel_id == child.id)
    ).one()
    assert nested.parent_channel_id == parent.id
    session.add(
        DeviceChannelVersion(
            channel_id=parent.id,
            catalog_ref="CH-1",
            parent_channel_id=parent.id,
            last_modified=at(1),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_identical_last_modified_does_not_create_second_device_version(session: Session) -> None:
    installation = persist_installation(session)
    device = persist_device(session, installation, title="v1", last_modified=at(0))
    session.add(
        DeviceVersion(
            device_id=device.id,
            title="v1-again",
            last_modified=at(0),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
