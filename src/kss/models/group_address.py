"""Paket GroupAddress: ETS GroupAddress (``GA-n``), Geschwister von GroupRange.

KIM ``knx:FunctionPoint`` ist nur ``meta.@type``, nicht der Entitätsname.
3API JSON:API type ``datapoint`` ist das Kommunikationsobjekt (``comm_objects``).
3API JSON:API type ``function`` ist die Gruppenadresse (``group_addresses``).
Katalog ``master_function_points`` (``FP-*``) ist eine andere Entität.

Runtime value/timestamp und datapointProxy sind Lücken (nicht modelliert).
Enum/Unit/Min/Max stehen auf datafields, nicht hier. ``group_address`` ist
der 16-Bit-Integer (Busnummer); Anzeige aus
``installation_versions.group_address_style``.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

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


class GroupAddress(Base):
    """Stabile Identität einer ETS-Gruppenadresse (``GA-n``).

    KIM ``knx:FunctionPoint`` nur als ``at_type``. 3API JSON:API type ``function``.
    Nicht 3API ``datapoint`` (das ist CommObject).
    """

    __tablename__ = "group_addresses"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_group_addresses_installation_ets_id",
        ),
        Index("ix_group_addresses_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment=(
            "Stabile UUID. ETS GroupAddress (GA-n). "
            "Nicht 3API datapoint (das ist CommObject). "
            "KIM knx:FunctionPoint liegt auf Version.at_type."
        ),
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

    versions: Mapped[list[GroupAddressVersion]] = relationship(
        order_by="GroupAddressVersion.last_modified",
    )


class GroupAddressVersion(TemporalVersionMixin, Base):
    """Version der GA-Attribute. ``group_address`` ist der 16-Bit-Integer."""

    __tablename__ = "group_address_versions"
    __table_args__ = (
        version_primary_key("group_address_id"),
        CheckConstraint(
            "group_address IS NULL OR (group_address >= 0 AND group_address <= 65535)",
            name="group_address",
        ),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_group_address_versions_group_address", "group_address"),
        Index("ix_group_address_versions_group_range_id", "group_range_id"),
    )

    group_address_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_addresses.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK zur GroupAddress-Identität, nicht die Busnummer.",
    )
    # Temporary: keep existing attribute access during APIler/service follow-up.
    datapoint_id = synonym("group_address_id")
    name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "ETS GroupAddress/@Name. Nicht 3API datapoint title "
            "(das ist CommObject)."
        ),
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_address: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "16-Bit GroupAddress/@Address / knx:groupAddress (Busnummer). "
            "Nicht die Entitäts-UUID. Anzeige aus Stil + diesem Integer."
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
            "KIM/JSON-LD @type (z. B. knx:FunctionPoint, knx:dpa.417.61). "
            "FunctionPoint ist @type, nicht die Tabelle. "
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


# Temporary aliases so APIler/services can follow without a freeze.
Datapoint = GroupAddress
DatapointVersion = GroupAddressVersion
