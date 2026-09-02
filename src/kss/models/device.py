"""Paket Device: 3API Device + Channel/Folder/CommObject + KO↔GA.

``assigned_trade`` wird nicht als Devicespalte modelliert (Name nicht eindeutig;
Zuordnung über temporale trade_devices). Channel-Kanon: ChannelInstance/@Id.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kss.models.base import Base
from kss.models.constants import COMPLETION_STATUS_SQL
from kss.models.temporal import TemporalVersionMixin, version_primary_key


class Device(Base):
    """Stabile Identität eines Geräts (3API ``data.id``)."""

    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_devices_installation_ets_id",
        ),
        Index("ix_devices_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API DeviceTypeAndId.id (uuid).",
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. knxproj-Suffix DI-n. TTL prj:DI-n.",
    )
    puid: Mapped[int | None] = mapped_column(Integer, nullable=True)

    versions: Mapped[list[DeviceVersion]] = relationship(
        back_populates="device",
        order_by="DeviceVersion.last_modified",
    )


class DeviceVersion(TemporalVersionMixin, Base):
    """Geräteversion. ETS-Semantik versioniert mit ``last_modified``;
    BUS-Bindings materialisiert separat (siehe ``kss.models.bus_bindings``)."""

    __tablename__ = "device_versions"
    __table_args__ = (
        version_primary_key("device_id"),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_device_versions_location_id", "location_id"),
        Index("ix_device_versions_segment_id", "segment_id"),
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="3API title. knxproj @Name wenn gesetzt, sonst Produktname.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_downloaded: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "3API lastDownloaded / LastDownload. Sentinel 0001-01-01 nicht speichern "
            "(kein echter Download)."
        ),
    )
    current_date_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    serial_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "3API serialNumber. Eine Spalte: 12 Hex-Zeichen der 6 Bytes "
            "(TTL $hex, XML Base64 → Importer wandelt)."
        ),
    )
    individual_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API individualAddress (z. B. 1.0.248). TTL hex ohne 0x.",
    )
    firmware_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    hardware_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="CompletionStatus / core:state.",
    )
    communication_part_loaded: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment=(
            "Kategorie 3. CommunicationPartLoaded. Allein kein Nachweis für "
            "LastDownload (Dummy-IP-Geräte)."
        ),
    )
    individual_address_loaded: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Kategorie 3. IndividualAddressLoaded.",
    )
    application_program_loaded: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Kategorie 3. ApplicationProgramLoaded.",
    )
    parameters_loaded: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Kategorie 3. ParametersLoaded.",
    )
    medium_config_loaded: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Kategorie 3. MediumConfigLoaded.",
    )
    product_ref: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. DeviceInstance/@ProductRefId.",
    )
    application_program_ref: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Hardware2Program / ApplicationProgram.",
    )
    bus_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installation_hints: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. InstallationHints (RTF möglich).",
    )
    at_type: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    type_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
        comment="3API relationships.deviceLocation.",
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Kategorie 3. Device hängt am Segment (Topology).",
    )

    device: Mapped[Device] = relationship(back_populates="versions")


class DeviceChannel(Base):
    """ChannelInstance. Kanonische Id: ChannelInstance/@Id (DI-n_CI-n)."""

    __tablename__ = "device_channels"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "ets_id",
            name="uq_device_channels_device_ets_id",
        ),
        Index("ix_device_channels_device_id", "device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. ChannelInstance-Fragment, z. B. CI-9 oder DI-65_CI-9.",
    )

    versions: Mapped[list[DeviceChannelVersion]] = relationship(
        back_populates="channel",
        order_by="DeviceChannelVersion.last_modified",
    )


class DeviceChannelVersion(TemporalVersionMixin, Base):
    __tablename__ = "device_channel_versions"
    __table_args__ = (version_primary_key("channel_id"),)

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_channels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_ref: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. ChannelInstance/@RefId, z. B. CH-3 oder MD-…_CH-4.",
    )

    channel: Mapped[DeviceChannel] = relationship(back_populates="versions")


class DeviceFolder(Base):
    """GroupObjectTree Folder (Node Type=Folder), knxproj-only."""

    __tablename__ = "device_folders"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "ets_id",
            name="uq_device_folders_device_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. Folder RefId, z. B. PB-47.",
    )

    versions: Mapped[list[DeviceFolderVersion]] = relationship(
        back_populates="folder",
        foreign_keys="DeviceFolderVersion.folder_id",
        order_by="DeviceFolderVersion.last_modified",
    )


class DeviceFolderVersion(TemporalVersionMixin, Base):
    __tablename__ = "device_folder_versions"
    __table_args__ = (
        version_primary_key("folder_id"),
        CheckConstraint(
            "parent_folder_id IS DISTINCT FROM folder_id",
            name="parent_not_self",
        ),
    )

    folder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_folders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_folders.id", ondelete="RESTRICT"),
        nullable=True,
    )

    folder: Mapped[DeviceFolder] = relationship(
        back_populates="versions",
        foreign_keys=[folder_id],
    )


class CommObject(Base):
    """Kommunikationsobjekt (ComObjectInstanceRef). Nicht der 3API-Datapoint."""

    __tablename__ = "comm_objects"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "ets_id",
            name="uq_comm_objects_device_ets_id",
        ),
        Index("ix_comm_objects_device_id", "device_id"),
        Index("ix_comm_objects_channel_id", "channel_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. RefId-Suffix O-…_R-…. TTL core:Datapoint (nicht GA).",
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_channels.id", ondelete="RESTRICT"),
        nullable=True,
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("device_folders.id", ondelete="RESTRICT"),
        nullable=True,
    )

    versions: Mapped[list[CommObjectVersion]] = relationship(
        back_populates="comm_object",
        order_by="CommObjectVersion.last_modified",
    )


class CommObjectVersion(TemporalVersionMixin, Base):
    """CO-Version. Flags und DPT bus-relevant (LastDownload + Flag); Name/Text nicht."""
    __tablename__ = "comm_object_versions"
    __table_args__ = (version_primary_key("comm_object_id"),)

    comm_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comm_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    datapoint_subtype_ets_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    communication_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    read_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    write_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    transmit_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    update_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    read_on_init_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    priority: Mapped[str | None] = mapped_column(Text, nullable=True)

    comm_object: Mapped[CommObject] = relationship(back_populates="versions")


class CommObjectDatapoint(TemporalVersionMixin, Base):
    """Temporale N:M-Kante KO ↔ GA (core:groups / ComObjectInstanceRef/@Links)."""

    __tablename__ = "comm_object_datapoints"
    __table_args__ = (
        version_primary_key("comm_object_id", "datapoint_id"),
        Index("ix_comm_object_datapoints_datapoint_id", "datapoint_id"),
    )

    comm_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comm_objects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    datapoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datapoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    linked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="false = Entkopplung ab diesem last_modified.",
    )
