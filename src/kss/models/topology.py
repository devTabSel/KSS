"""Paket Topology: Area / Line / Segment (nur knxproj, nicht im TTL)."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kss.models.base import Base
from kss.models.constants import COMPLETION_STATUS_SQL
from kss.models.temporal import TemporalVersionMixin, version_primary_key

ADDRESS_SQL = "address >= 0 AND address <= 15"


class Area(Base):
    """Stabile Identität eines ETS-Bereichs (``A-n``)."""

    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_areas_installation_ets_id",
        ),
        Index("ix_areas_installation_id", "installation_id"),
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
        comment="Kategorie 3. knxproj-Suffix, z. B. A-1. Nicht im TTL.",
    )

    versions: Mapped[list[AreaVersion]] = relationship(
        back_populates="area",
        order_by="AreaVersion.last_modified",
    )


class AreaVersion(TemporalVersionMixin, Base):
    __tablename__ = "area_versions"
    __table_args__ = (
        version_primary_key("area_id"),
        CheckConstraint(ADDRESS_SQL, name="address"),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
    )

    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Area/@Address (0–15), unabhängig von ets_id.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    area: Mapped[Area] = relationship(back_populates="versions")


class Line(Base):
    """Stabile Identität einer ETS-Linie (``L-n``)."""

    __tablename__ = "lines"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_lines_installation_ets_id",
        ),
        Index("ix_lines_installation_id", "installation_id"),
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
        comment="Kategorie 3. knxproj-Suffix, z. B. L-1. Nicht im TTL.",
    )

    versions: Mapped[list[LineVersion]] = relationship(
        back_populates="line",
        order_by="LineVersion.last_modified",
    )


class LineVersion(TemporalVersionMixin, Base):
    __tablename__ = "line_versions"
    __table_args__ = (
        version_primary_key("line_id"),
        CheckConstraint(ADDRESS_SQL, name="address"),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_line_versions_area_id", "area_id"),
    )

    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Line/@Address (0–15).",
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    medium_type_ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. MediumTypeRefId, z. B. MT-0.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    line: Mapped[Line] = relationship(back_populates="versions")


class Segment(Base):
    """Stabile Identität eines ETS-Segments (``S-n``). Device hängt hier."""

    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_segments_installation_ets_id",
        ),
        Index("ix_segments_installation_id", "installation_id"),
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
        comment="Kategorie 3. knxproj-Suffix, z. B. S-1. Nicht im TTL.",
    )

    versions: Mapped[list[SegmentVersion]] = relationship(
        back_populates="segment",
        order_by="SegmentVersion.last_modified",
    )


class SegmentVersion(TemporalVersionMixin, Base):
    __tablename__ = "segment_versions"
    __table_args__ = (
        version_primary_key("segment_id"),
        CheckConstraint(
            "medium_type_ets_id IS NULL OR medium_type_ets_id <> ''",
            name="medium_type_ets_id_not_empty",
        ),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_segment_versions_line_id", "line_id"),
    )

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    medium_type_ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. MediumTypeRefId am Segment.",
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    number: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Number.")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    segment: Mapped[Segment] = relationship(back_populates="versions")
