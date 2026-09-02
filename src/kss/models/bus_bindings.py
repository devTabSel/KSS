"""Materialisierte BUS-Indizes (abgeleitet beim Device-Import).

Getrennt von ETS-Versionstabellen. Telegramm-Auswertung nutzt diese Tabellen
für PA→Device und GA+Device→Binding; semantische Attribute kommen danach aus
``E(entity, t)`` auf ``*_versions``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from kss.models.base import Base


class BusPaBinding(Base):
    """PA → Device zum Zeitpunkt ``last_downloaded`` (BUS-wirksam)."""

    __tablename__ = "bus_pa_bindings"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(individual_address)) > 0",
            name="individual_address",
        ),
        Index(
            "ix_bus_pa_bindings_lookup",
            "installation_id",
            "individual_address",
            "last_downloaded",
        ),
    )

    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    individual_address: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        nullable=False,
        comment="3API-Punktnotation, z. B. 1.0.248.",
    )
    last_downloaded: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        comment="BUS-Wirksamkeit; Sentinel 0001-01-01 nie speichern.",
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )


class BusGaBinding(Base):
    """GA + Device → Binding zum Zeitpunkt ``last_downloaded``."""

    __tablename__ = "bus_ga_bindings"
    __table_args__ = (
        CheckConstraint(
            "group_address >= 0 AND group_address <= 65535",
            name="group_address",
        ),
        Index(
            "ix_bus_ga_bindings_lookup",
            "installation_id",
            "group_address",
            "last_downloaded",
        ),
    )

    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    group_address: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="16-Bit bus-wirksamer Integer zum Download-Stand.",
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    last_downloaded: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
