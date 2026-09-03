import uuid
from datetime import UTC, datetime

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
from kss.models.location import (
    Function,
    FunctionDatapoint,
    FunctionVersion,
    Location,
    LocationVersion,
)
from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.models.trade import Trade, TradeDevice, TradeVersion


def at(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, 0, 0, tzinfo=UTC)


def persist_installation(
    session: Session,
    *,
    title: str = "WA53H10",
    ets_id: str = "P-040E-0",
    project_guid: uuid.UUID | None = None,
    last_modified: datetime | None = None,
    last_import: datetime | None = None,
    project_start: datetime | None = None,
    **version_fields: object,
) -> Installation:
    installation = Installation(
        id=uuid.uuid4(),
        ets_id=ets_id,
        project_guid=project_guid or uuid.uuid4(),
        last_import=last_import or at(1),
        project_start=project_start,
    )
    session.add(installation)
    session.flush()
    fields = {"group_address_style": "ThreeLevel", **version_fields}
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title=title,
            last_modified=last_modified or at(0),
            **fields,
        )
    )
    session.flush()
    return installation


def persist_location(
    session: Session,
    installation: Installation,
    *,
    title: str = "EG",
    ets_id: str = "BP-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> Location:
    location = Location(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(location)
    session.flush()
    session.add(
        LocationVersion(
            location_id=location.id,
            title=title,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return location


def persist_area_line_segment(
    session: Session,
    installation: Installation,
) -> tuple[Segment, uuid.UUID]:
    area = Area(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id="A-1",
    )
    session.add(area)
    session.flush()
    session.add(
        AreaVersion(
            area_id=area.id,
            name="Bereich 1",
            address=1,
            last_modified=at(0),
        )
    )
    line = Line(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id="L-1",
    )
    session.add(line)
    session.flush()
    session.add(
        LineVersion(
            line_id=line.id,
            name="Linie 0",
            address=0,
            area_id=area.id,
            medium_type_ets_id="MT-0",
            last_modified=at(0),
        )
    )
    segment = Segment(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id="S-1",
    )
    session.add(segment)
    session.flush()
    session.add(
        SegmentVersion(
            segment_id=segment.id,
            name="Segment 0",
            line_id=line.id,
            last_modified=at(0),
        )
    )
    session.flush()
    return segment, line.id


def persist_device(
    session: Session,
    installation: Installation,
    *,
    title: str = "Aktor",
    ets_id: str = "DI-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> Device:
    device = Device(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(device)
    session.flush()
    session.add(
        DeviceVersion(
            device_id=device.id,
            title=title,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return device


def persist_channel(
    session: Session,
    device: Device,
    *,
    title: str | None = "Kanal",
    ets_id: str = "CH-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> DeviceChannel:
    channel = DeviceChannel(
        id=uuid.uuid4(),
        device_id=device.id,
        ets_id=ets_id,
    )
    session.add(channel)
    session.flush()
    session.add(
        DeviceChannelVersion(
            channel_id=channel.id,
            title=title,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return channel


def persist_folder(
    session: Session,
    device: Device,
    *,
    title: str | None = "Ordner",
    ets_id: str = "PB-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> DeviceFolder:
    folder = DeviceFolder(
        id=uuid.uuid4(),
        device_id=device.id,
        ets_id=ets_id,
    )
    session.add(folder)
    session.flush()
    session.add(
        DeviceFolderVersion(
            folder_id=folder.id,
            title=title,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return folder


def persist_comm_object(
    session: Session,
    device: Device,
    *,
    name: str | None = "Schalt",
    ets_id: str = "O-1_R-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> CommObject:
    comm_object = CommObject(
        id=uuid.uuid4(),
        device_id=device.id,
        ets_id=ets_id,
    )
    session.add(comm_object)
    session.flush()
    session.add(
        CommObjectVersion(
            comm_object_id=comm_object.id,
            name=name,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return comm_object


def persist_comm_object_datapoint(
    session: Session,
    comm_object: CommObject,
    datapoint: Datapoint,
    *,
    last_modified: datetime | None = None,
    linked: bool = True,
) -> CommObjectDatapoint:
    edge = CommObjectDatapoint(
        comm_object_id=comm_object.id,
        datapoint_id=datapoint.id,
        last_modified=last_modified or at(0),
        linked=linked,
    )
    session.add(edge)
    session.flush()
    return edge


def persist_group_range(
    session: Session,
    installation: Installation,
    *,
    name: str = "Licht",
    ets_id: str = "GR-1",
    range_start: int | None = 256,
    range_end: int | None = 511,
    last_modified: datetime | None = None,
    **version_fields: object,
) -> GroupRange:
    group_range = GroupRange(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(group_range)
    session.flush()
    session.add(
        GroupRangeVersion(
            group_range_id=group_range.id,
            name=name,
            range_start=range_start,
            range_end=range_end,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return group_range


def persist_datapoint(
    session: Session,
    installation: Installation,
    *,
    title: str = "Licht schalten",
    ets_id: str = "GA-1",
    group_address: int | None = 30720,
    last_modified: datetime | None = None,
    **version_fields: object,
) -> Datapoint:
    datapoint = Datapoint(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(datapoint)
    session.flush()
    session.add(
        DatapointVersion(
            datapoint_id=datapoint.id,
            name=title,
            group_address=group_address,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return datapoint


def persist_function(
    session: Session,
    installation: Installation,
    *,
    title: str = "Beleuchtung",
    ets_id: str = "F-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> Function:
    function = Function(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(function)
    session.flush()
    fields = {"function_type_ets_id": "FT-0", **version_fields}
    session.add(
        FunctionVersion(
            function_id=function.id,
            title=title,
            last_modified=last_modified or at(0),
            **fields,
        )
    )
    session.flush()
    return function


def persist_function_datapoint(
    session: Session,
    function: Function,
    datapoint: Datapoint,
    *,
    last_modified: datetime | None = None,
    linked: bool = True,
    **fields: object,
) -> FunctionDatapoint:
    edge = FunctionDatapoint(
        function_id=function.id,
        datapoint_id=datapoint.id,
        last_modified=last_modified or at(0),
        linked=linked,
        **fields,
    )
    session.add(edge)
    session.flush()
    return edge


def persist_trade_device(
    session: Session,
    trade: Trade,
    device: Device,
    *,
    last_modified: datetime | None = None,
    linked: bool = True,
) -> TradeDevice:
    edge = TradeDevice(
        trade_id=trade.id,
        device_id=device.id,
        last_modified=last_modified or at(0),
        linked=linked,
    )
    session.add(edge)
    session.flush()
    return edge


def persist_trade(
    session: Session,
    installation: Installation,
    *,
    name: str = "Lighting",
    ets_id: str = "T-1",
    last_modified: datetime | None = None,
    **version_fields: object,
) -> Trade:
    trade = Trade(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(trade)
    session.flush()
    session.add(
        TradeVersion(
            trade_id=trade.id,
            name=name,
            last_modified=last_modified or at(0),
            **version_fields,
        )
    )
    session.flush()
    return trade
