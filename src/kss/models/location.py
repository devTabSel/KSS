"""Paket Location: 3API Location + ETS Space + ApplicationFunction.

ETS-Funktionen gehören hierher (TTL core:ApplicationFunction,
loc:hasApplicationFunction). Kein eigenes Function-Paket.
core:Functionality (UUID-Beutel aller COs) wird nicht persistiert.
prj:Site ist nicht die Installation; optionale synthetische Ortswurzel.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kss.models.base import Base
from kss.models.constants import COMPLETION_STATUS_SQL, LOCATION_TYPE_SQL
from kss.models.temporal import TemporalVersionMixin, version_primary_key


class Location(Base):
    """Stabile Identität eines Orts (3API ``data.id``)."""

    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_locations_installation_ets_id",
        ),
        Index("ix_locations_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API LocationTypeAndId.id (uuid).",
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. knxproj-Suffix BP-n. TTL prj:BP-n.",
    )

    versions: Mapped[list[LocationVersion]] = relationship(
        back_populates="location",
        foreign_keys="LocationVersion.location_id",
        order_by="LocationVersion.last_modified",
    )


class LocationVersion(TemporalVersionMixin, Base):
    """Gültigkeitsversion der Ortsattribute.

    ``location_type`` = XSD SpaceType_t, nicht knx_master.
    ``usage`` = SU-* oder ETS-6.4-KIM-Tag (tag:bedroom).
    """

    __tablename__ = "location_versions"
    __table_args__ = (
        version_primary_key("location_id"),
        CheckConstraint(
            "parent_location_id IS DISTINCT FROM location_id",
            name="parent_not_self",
        ),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        CheckConstraint(LOCATION_TYPE_SQL, name="location_type"),
        Index("ix_location_versions_parent_location_id", "parent_location_id"),
        Index("ix_location_versions_default_line_id", "default_line_id"),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK zur stabilen Orts-Identität.",
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="3API attributes.title. Synthetisches Site-Dummy nicht als echte Daten behandeln.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Space/@Number.",
    )
    location_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Space/@Type (SpaceType_t).",
    )
    usage: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Space/@Usage (SU-* oder tag:bedroom).",
    )
    completion_status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="CompletionStatus / core:state.",
    )
    at_type: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="3API item.meta.@type (z. B. loc:Building, loc:Site).",
    )
    parent_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
        comment="3API relationships.parentLocation. NULL = Wurzel.",
    )
    default_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lines.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Kategorie 3. Space/@DefaultLine → lines.id.",
    )

    location: Mapped[Location] = relationship(
        back_populates="versions",
        foreign_keys=[location_id],
    )
    parent_location: Mapped[Location | None] = relationship(
        foreign_keys=[parent_location_id],
    )


class Function(Base):
    """Stabile Identität einer ETS-/3API-Funktion (``F-n``, core:ApplicationFunction)."""

    __tablename__ = "functions"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_functions_installation_ets_id",
        ),
        Index("ix_functions_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API FunctionTypeAndId.id (uuid).",
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. knxproj-Suffix F-n. TTL prj:F-n.",
    )

    versions: Mapped[list[FunctionVersion]] = relationship(
        back_populates="function",
        order_by="FunctionVersion.last_modified",
    )


class FunctionVersion(TemporalVersionMixin, Base):
    __tablename__ = "function_versions"
    __table_args__ = (
        version_primary_key("function_id"),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_function_versions_location_id", "location_id"),
    )

    function_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("functions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    function_type_ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. FunctionType FT-*. WA53H10 oft FT-0 (custom).",
    )
    at_type: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="3API meta.@type; TTL core:ApplicationFunction.",
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
        comment="3API relationships.functionLocation / loc:hasApplicationFunction.",
    )
    completion_status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="CompletionStatus / core:state. Nicht unter /api/v1.",
    )

    function: Mapped[Function] = relationship(back_populates="versions")


class FunctionDatapoint(TemporalVersionMixin, Base):
    """Temporale Kante Function ↔ Datapoint (GroupAddressRef / knx:hasFunctionPoint).

    Unlink = neue Zeile mit ``linked=false``. ``role`` darf ``DR-*`` oder freie UUID sein.
    """

    __tablename__ = "function_datapoints"
    __table_args__ = (
        version_primary_key("function_id", "datapoint_id"),
        Index("ix_function_datapoints_datapoint_id", "datapoint_id"),
    )

    function_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("functions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    datapoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datapoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. GroupAddressRef/@Id, z. B. GF-1.",
    )
    role: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. GroupAddressRef/@Role (DR-* oder UUID). TTL hat kein Role.",
    )
    linked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="false = Entkopplung ab diesem last_modified.",
    )
