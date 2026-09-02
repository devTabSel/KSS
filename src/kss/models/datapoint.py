"""Paket Datapoint: 3API Datapoint = knxproj GroupAddress = TTL knx:FunctionPoint.

CommObjects sind nicht dieser Datapoint. Runtime value/timestamp und
datapointProxy sind Lücken (nicht modelliert). Enum/Unit/Min/Max stehen
auf datafields, nicht hier. ``group_address`` ist der 16-Bit-Integer;
Anzeige aus ``installation_versions.group_address_style``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class GroupRange(Base):
    """Stabile Identität eines GroupRange (``GR-n``, nur knxproj)."""

    __tablename__ = "group_ranges"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_group_ranges_installation_ets_id",
        ),
        Index("ix_group_ranges_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. knxproj-Suffix GR-n. Nicht im TTL.",
    )

    versions: Mapped[list[GroupRangeVersion]] = relationship(
        back_populates="group_range",
        foreign_keys="GroupRangeVersion.group_range_id",
        order_by="GroupRangeVersion.last_modified",
    )


class GroupRangeVersion(TemporalVersionMixin, Base):
    __tablename__ = "group_range_versions"
    __table_args__ = (
        version_primary_key("group_range_id"),
        CheckConstraint(
            "parent_group_range_id IS DISTINCT FROM group_range_id",
            name="parent_not_self",
        ),
        CheckConstraint(
            "range_start IS NULL OR (range_start >= 0 AND range_start <= 65535)",
            name="range_start",
        ),
        CheckConstraint(
            "range_end IS NULL OR (range_end >= 0 AND range_end <= 65535)",
            name="range_end",
        ),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_group_range_versions_parent_group_range_id", "parent_group_range_id"),
    )

    group_range_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_ranges.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_group_range_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_ranges.id", ondelete="RESTRICT"),
        nullable=True,
    )
    range_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    range_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unfiltered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    security: Mapped[str | None] = mapped_column(Text, nullable=True)

    group_range: Mapped[GroupRange] = relationship(
        back_populates="versions",
        foreign_keys=[group_range_id],
    )


class Datapoint(Base):
    """Stabile Identität einer Gruppenadresse / 3API-Datapoint."""

    __tablename__ = "datapoints"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_datapoints_installation_ets_id",
        ),
        Index("ix_datapoints_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API DatapointTypeAndId.id (uuid).",
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. knxproj-Suffix GA-n. TTL prj:GA-n.",
    )

    versions: Mapped[list[DatapointVersion]] = relationship(
        back_populates="datapoint",
        order_by="DatapointVersion.last_modified",
    )


class DatapointVersion(TemporalVersionMixin, Base):
    """Version der GA-Attribute. ``group_address`` ist der 16-Bit-Integer."""

    __tablename__ = "datapoint_versions"
    __table_args__ = (
        version_primary_key("datapoint_id"),
        CheckConstraint(
            "group_address IS NULL OR (group_address >= 0 AND group_address <= 65535)",
            name="group_address",
        ),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_datapoint_versions_group_address", "group_address"),
        Index("ix_datapoint_versions_group_range_id", "group_range_id"),
    )

    datapoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datapoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API title unter /api/v1.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_address: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "16-Bit GroupAddress/@Address / knx:groupAddress. "
            "Anzeige aus Stil + diesem Integer, keine Haupt-/Mittelgruppe-Spalten."
        ),
    )
    datapoint_subtype_ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Token DPST-x-y / DPT-x.",
    )
    at_type: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment=(
            "3API item.meta.@type (z. B. knx:FunctionPoint, knx:dpa.417.61). "
            "Fill/Synthese mit Tag-Store, nicht Ingest-Pflicht."
        ),
    )
    readable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    writable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    security: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_range_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_ranges.id", ondelete="RESTRICT"),
        nullable=True,
    )
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    unfiltered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    central: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    global_: Mapped[bool | None] = mapped_column(
        "global",
        Boolean,
        nullable=True,
        comment="@Global.",
    )
    key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="XML @Key / KNX Data Secure Gruppenkey.",
    )

    datapoint: Mapped[Datapoint] = relationship(back_populates="versions")
