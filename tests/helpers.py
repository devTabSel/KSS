import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from kss.models.datapoint import Datapoint, DatapointVersion
from kss.models.device import Device, DeviceVersion
from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionVersion, Location, LocationVersion
from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.models.trade import Trade, TradeVersion


def at(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, 0, 0, tzinfo=UTC)


def persist_installation(
    session: Session,
    *,
    title: str = "WA53H10",
    ets_id: str | None = "P-040E-0",
    since: datetime | None = None,
    observable_since: datetime | None = None,
    **version_fields: object,
) -> Installation:
    installation = Installation(
        id=uuid.uuid4(),
        ets_id=ets_id,
        knx_project_id="P-040E" if ets_id else None,
        installation_index=0 if ets_id else None,
        group_address_style="ThreeLevel",
    )
    session.add(installation)
    session.flush()
    session.add(
        InstallationVersion(
            installation_id=installation.id,
            title=title,
            _since=since or at(0),
            _observable_since=observable_since or at(1),
            **version_fields,
        )
    )
    session.flush()
    return installation


def persist_location(
    session: Session,
    installation: Installation,
    *,
    title: str = "EG",
    ets_id: str | None = "BP-1",
    since: datetime | None = None,
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
            _since=since or at(0),
            _observable_since=at(1),
            **version_fields,
        )
    )
    session.flush()
    return location


def persist_area_line_segment(
    session: Session,
    installation: Installation,
) -> Segment:
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
            _since=at(0),
            _observable_since=at(1),
        )
    )
    line = Line(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id="L-1",
        area_id=area.id,
    )
    session.add(line)
    session.flush()
    session.add(
        LineVersion(
            line_id=line.id,
            name="Linie 0",
            address=0,
            medium_type_ets_id="MT-0",
            _since=at(0),
            _observable_since=at(1),
        )
    )
    segment = Segment(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id="S-1",
        line_id=line.id,
    )
    session.add(segment)
    session.flush()
    session.add(
        SegmentVersion(
            segment_id=segment.id,
            name="Segment 0",
            _since=at(0),
            _observable_since=at(1),
        )
    )
    session.flush()
    return segment


def persist_device(
    session: Session,
    installation: Installation,
    *,
    title: str = "Aktor",
    ets_id: str | None = "DI-1",
    since: datetime | None = None,
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
            _since=since or at(0),
            _observable_since=at(1),
            **version_fields,
        )
    )
    session.flush()
    return device


def persist_datapoint(
    session: Session,
    installation: Installation,
    *,
    title: str = "Licht schalten",
    ets_id: str | None = "GA-1",
    group_address: int | None = 30720,
    since: datetime | None = None,
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
            title=title,
            group_address=group_address,
            _since=since or at(0),
            _observable_since=at(1),
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
    ets_id: str | None = "F-1",
    since: datetime | None = None,
    **version_fields: object,
) -> Function:
    function = Function(
        id=uuid.uuid4(),
        installation_id=installation.id,
        ets_id=ets_id,
    )
    session.add(function)
    session.flush()
    session.add(
        FunctionVersion(
            function_id=function.id,
            title=title,
            _since=since or at(0),
            _observable_since=at(1),
            **version_fields,
        )
    )
    session.flush()
    return function


def persist_trade(
    session: Session,
    installation: Installation,
    *,
    name: str = "Lighting",
    ets_id: str | None = "T-1",
    since: datetime | None = None,
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
            _since=since or at(0),
            _observable_since=at(1),
            **version_fields,
        )
    )
    session.flush()
    return trade
