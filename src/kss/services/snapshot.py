"""Installation snapshot at time ``t`` = ``E(entity, t)`` for every package.

``contributions`` is the extension point for facts that are not native columns:
knxproj trades projected into TTL, and later Tag-Store / custom entities that
may supply XSD23 XML and/or Turtle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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
from kss.services.temporal import isoformat_utc, version_at


@dataclass(frozen=True)
class TtlStatement:
    """One RDF statement. ``subject`` is a ``prj:`` fragment (``DI-1``, ``T-14``)."""

    subject: str
    predicate: str
    object: str
    object_kind: Literal["prj", "curie", "literal", "datetime", "bool", "int"] = (
        "literal"
    )


@dataclass(frozen=True)
class XmlFragment:
    """XSD23 element to merge under ``parent_id`` (knxproj ``@Id``)."""

    parent_id: str
    tag: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class ExportContributions:
    """Extra facts for both serializers. Tag-Store fills this later."""

    ttl: tuple[TtlStatement, ...] = ()
    xml: tuple[XmlFragment, ...] = ()


@dataclass
class LocationSnap:
    location: Location
    version: LocationVersion


@dataclass
class FunctionSnap:
    function: Function
    version: FunctionVersion


@dataclass
class AreaSnap:
    area: Area
    version: AreaVersion


@dataclass
class LineSnap:
    line: Line
    version: LineVersion


@dataclass
class SegmentSnap:
    segment: Segment
    version: SegmentVersion


@dataclass
class DeviceSnap:
    device: Device
    version: DeviceVersion


@dataclass
class ChannelSnap:
    channel: DeviceChannel
    version: DeviceChannelVersion


@dataclass
class FolderSnap:
    folder: DeviceFolder
    version: DeviceFolderVersion


@dataclass
class CommObjectSnap:
    comm_object: CommObject
    version: CommObjectVersion


@dataclass
class DatapointSnap:
    datapoint: Datapoint
    version: DatapointVersion


@dataclass
class GroupRangeSnap:
    group_range: GroupRange
    version: GroupRangeVersion


@dataclass
class TradeSnap:
    trade: Trade
    version: TradeVersion


@dataclass
class InstallationSnapshot:
    installation: Installation
    version: InstallationVersion
    at: datetime | None
    locations: list[LocationSnap] = field(default_factory=list)
    functions: list[FunctionSnap] = field(default_factory=list)
    areas: list[AreaSnap] = field(default_factory=list)
    lines: list[LineSnap] = field(default_factory=list)
    segments: list[SegmentSnap] = field(default_factory=list)
    devices: list[DeviceSnap] = field(default_factory=list)
    channels: list[ChannelSnap] = field(default_factory=list)
    folders: list[FolderSnap] = field(default_factory=list)
    comm_objects: list[CommObjectSnap] = field(default_factory=list)
    datapoints: list[DatapointSnap] = field(default_factory=list)
    group_ranges: list[GroupRangeSnap] = field(default_factory=list)
    trades: list[TradeSnap] = field(default_factory=list)
    function_datapoints: list[FunctionDatapoint] = field(default_factory=list)
    comm_object_datapoints: list[CommObjectDatapoint] = field(default_factory=list)
    trade_devices: list[TradeDevice] = field(default_factory=list)
    contributions: ExportContributions = field(default_factory=ExportContributions)


def snapshot_installation(
    session: Session,
    installation_id: UUID,
    at: datetime | None,
) -> InstallationSnapshot | None:
    installation = session.get(
        Installation,
        installation_id,
        options=(selectinload(Installation.versions),),
    )
    if installation is None:
        return None
    version = version_at(installation.versions, at)
    if version is None:
        return None
    snap = InstallationSnapshot(
        installation=installation, version=version, at=at
    )
    _load_locations(session, snap)
    _load_functions(session, snap)
    _load_topology(session, snap)
    _load_devices(session, snap)
    _load_device_parts(session, snap)
    _load_datapoints(session, snap)
    _load_trades(session, snap)
    snap.contributions = collect_contributions(session, snap)
    return snap


def collect_contributions(
    session: Session, snap: InstallationSnapshot
) -> ExportContributions:
    """Union of derived facts. Custom tags/entities hook in here later."""
    del session
    ttl = list(_knxproj_trades_to_ttl(snap))
    ttl.extend(_custom_tag_ttl(snap))
    xml = list(_custom_tag_xml(snap))
    return ExportContributions(ttl=tuple(ttl), xml=tuple(xml))


def _knxproj_trades_to_ttl(snap: InstallationSnapshot) -> list[TtlStatement]:
    """Project ETS ``T-n`` / ``trade_devices`` into Turtle.

    Ingest persists ``prj:T-*`` and ``knx:hasDevice``. Device ``mac:assignedTrade``
    is filled from the linked trade name when the Device version has no TTL name.
    """
    statements: list[TtlStatement] = []
    trades = {item.trade.id: item for item in snap.trades}
    devices_by_id = {item.device.id: item for item in snap.devices}
    assigned: dict[UUID, str] = {}
    for edge in snap.trade_devices:
        trade_snap = trades.get(edge.trade_id)
        device_snap = devices_by_id.get(edge.device_id)
        if trade_snap is None or device_snap is None:
            continue
        statements.append(
            TtlStatement(
                trade_snap.trade.ets_id,
                "knx:hasDevice",
                device_snap.device.ets_id,
                "prj",
            )
        )
        if device_snap.version.assigned_trade is None:
            assigned.setdefault(device_snap.device.id, trade_snap.version.name)
    for item in snap.trades:
        ets_id = item.trade.ets_id
        statements.append(TtlStatement(ets_id, "rdf:type", "owl:NamedIndividual", "curie"))
        statements.append(
            TtlStatement(ets_id, "dct:title", item.version.name, "literal")
        )
        if item.version.description:
            statements.append(
                TtlStatement(
                    ets_id, "dct:description", item.version.description, "literal"
                )
            )
        if item.version.comment:
            statements.append(
                TtlStatement(ets_id, "core:comment", item.version.comment, "literal")
            )
        if item.version.number:
            statements.append(
                TtlStatement(ets_id, "core:number", item.version.number, "literal")
            )
        if item.version.completion_status:
            statements.append(
                TtlStatement(
                    ets_id, "core:state", item.version.completion_status, "literal"
                )
            )
        statements.append(
            TtlStatement(
                ets_id,
                "core:lastModified",
                isoformat_utc(item.version.last_modified),
                "datetime",
            )
        )
        parent_id = item.version.parent_trade_id
        if parent_id is not None and parent_id in trades:
            statements.append(
                TtlStatement(
                    trades[parent_id].trade.ets_id,
                    "knx:hasTrade",
                    ets_id,
                    "prj",
                )
            )
    for device_id, name in assigned.items():
        device_snap = devices_by_id[device_id]
        statements.append(
            TtlStatement(
                device_snap.device.ets_id,
                "mac:assignedTrade",
                name,
                "literal",
            )
        )
    return statements


def _custom_tag_ttl(snap: InstallationSnapshot) -> list[TtlStatement]:
    """Tag-Store / custom entities → Turtle. Empty until that packet exists."""
    del snap
    return []


def _custom_tag_xml(snap: InstallationSnapshot) -> list[XmlFragment]:
    """Tag-Store / custom entities → XSD23. Empty until that packet exists."""
    del snap
    return []


def _load_locations(session: Session, snap: InstallationSnapshot) -> None:
    rows = session.scalars(
        select(Location)
        .where(Location.installation_id == snap.installation.id)
        .options(selectinload(Location.versions))
        .order_by(Location.ets_id)
    ).all()
    for location in rows:
        version = version_at(location.versions, snap.at)
        if version is not None:
            snap.locations.append(LocationSnap(location, version))


def _load_functions(session: Session, snap: InstallationSnapshot) -> None:
    rows = session.scalars(
        select(Function)
        .where(Function.installation_id == snap.installation.id)
        .options(selectinload(Function.versions))
        .order_by(Function.ets_id)
    ).all()
    function_ids: list[UUID] = []
    for function in rows:
        version = version_at(function.versions, snap.at)
        if version is None:
            continue
        snap.functions.append(FunctionSnap(function, version))
        function_ids.append(function.id)
    if not function_ids:
        return
    edges = session.scalars(
        select(FunctionDatapoint).where(FunctionDatapoint.function_id.in_(function_ids))
    ).all()
    snap.function_datapoints = _linked_edges(
        edges, lambda item: (item.function_id, item.datapoint_id), snap.at
    )


def _load_topology(session: Session, snap: InstallationSnapshot) -> None:
    for model, attr, wrapper in (
        (Area, "areas", AreaSnap),
        (Line, "lines", LineSnap),
        (Segment, "segments", SegmentSnap),
    ):
        rows = session.scalars(
            select(model)
            .where(model.installation_id == snap.installation.id)
            .options(selectinload(model.versions))
            .order_by(model.ets_id)
        ).all()
        bucket: list = getattr(snap, attr)
        identity_key = {
            Area: "area",
            Line: "line",
            Segment: "segment",
        }[model]
        for row in rows:
            version = version_at(row.versions, snap.at)
            if version is not None:
                bucket.append(wrapper(**{identity_key: row, "version": version}))


def _load_devices(session: Session, snap: InstallationSnapshot) -> None:
    rows = session.scalars(
        select(Device)
        .where(Device.installation_id == snap.installation.id)
        .options(selectinload(Device.versions))
        .order_by(Device.ets_id)
    ).all()
    for device in rows:
        version = version_at(device.versions, snap.at)
        if version is not None:
            snap.devices.append(DeviceSnap(device, version))


def _load_device_parts(session: Session, snap: InstallationSnapshot) -> None:
    device_ids = [item.device.id for item in snap.devices]
    if not device_ids:
        return
    channels = session.scalars(
        select(DeviceChannel)
        .where(DeviceChannel.device_id.in_(device_ids))
        .options(selectinload(DeviceChannel.versions))
        .order_by(DeviceChannel.ets_id)
    ).all()
    for channel in channels:
        version = version_at(channel.versions, snap.at)
        if version is not None:
            snap.channels.append(ChannelSnap(channel, version))
    folders = session.scalars(
        select(DeviceFolder)
        .where(DeviceFolder.device_id.in_(device_ids))
        .options(selectinload(DeviceFolder.versions))
        .order_by(DeviceFolder.ets_id)
    ).all()
    for folder in folders:
        version = version_at(folder.versions, snap.at)
        if version is not None:
            snap.folders.append(FolderSnap(folder, version))
    comm_objects = session.scalars(
        select(CommObject)
        .where(CommObject.device_id.in_(device_ids))
        .options(selectinload(CommObject.versions))
        .order_by(CommObject.ets_id)
    ).all()
    co_ids: list[UUID] = []
    for comm_object in comm_objects:
        version = version_at(comm_object.versions, snap.at)
        if version is None:
            continue
        snap.comm_objects.append(CommObjectSnap(comm_object, version))
        co_ids.append(comm_object.id)
    if not co_ids:
        return
    edges = session.scalars(
        select(CommObjectDatapoint).where(
            CommObjectDatapoint.comm_object_id.in_(co_ids)
        )
    ).all()
    snap.comm_object_datapoints = _linked_edges(
        edges, lambda item: (item.comm_object_id, item.datapoint_id), snap.at
    )


def _load_datapoints(session: Session, snap: InstallationSnapshot) -> None:
    ranges = session.scalars(
        select(GroupRange)
        .where(GroupRange.installation_id == snap.installation.id)
        .options(selectinload(GroupRange.versions))
        .order_by(GroupRange.ets_id)
    ).all()
    for group_range in ranges:
        version = version_at(group_range.versions, snap.at)
        if version is not None:
            snap.group_ranges.append(GroupRangeSnap(group_range, version))
    rows = session.scalars(
        select(Datapoint)
        .where(Datapoint.installation_id == snap.installation.id)
        .options(selectinload(Datapoint.versions))
        .order_by(Datapoint.ets_id)
    ).all()
    for datapoint in rows:
        version = version_at(datapoint.versions, snap.at)
        if version is not None:
            snap.datapoints.append(DatapointSnap(datapoint, version))


def _load_trades(session: Session, snap: InstallationSnapshot) -> None:
    rows = session.scalars(
        select(Trade)
        .where(Trade.installation_id == snap.installation.id)
        .options(selectinload(Trade.versions))
        .order_by(Trade.ets_id)
    ).all()
    trade_ids: list[UUID] = []
    for trade in rows:
        version = version_at(trade.versions, snap.at)
        if version is None:
            continue
        snap.trades.append(TradeSnap(trade, version))
        trade_ids.append(trade.id)
    if not trade_ids:
        return
    edges = session.scalars(
        select(TradeDevice).where(TradeDevice.trade_id.in_(trade_ids))
    ).all()
    snap.trade_devices = _linked_edges(
        edges, lambda item: (item.trade_id, item.device_id), snap.at
    )


def _linked_edges(rows: list, key_fn, at: datetime | None) -> list:
    grouped: dict[tuple, list] = {}
    for row in rows:
        grouped.setdefault(key_fn(row), []).append(row)
    result = []
    for versions in grouped.values():
        current = version_at(versions, at)
        if current is not None and current.linked:
            result.append(current)
    return result
