"""Paket Trade: ETS-Gewerke (kein 3API-Resource-Typ, Kategorie 3).

Name darf kollidieren. Identität über ets_id (T-n). Device↔Trade ist temporal.
tag:lighting und mac:assignedTrade (Name) sind keine Trade-Identität.
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kss.models.base import Base
from kss.models.constants import COMPLETION_STATUS_SQL
from kss.models.temporal import TemporalVersionMixin, version_primary_key


class Trade(Base):
    """Stabile KSS-Identität eines ETS-Gewerks."""

    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_trades_installation_ets_id",
        ),
        Index("ix_trades_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="KSS Kategorie 3. Stabile Gewerk-Identität (UUID, nicht 3API).",
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. knxproj-Suffix T-n. Nicht im TTL.",
    )

    versions: Mapped[list[TradeVersion]] = relationship(
        back_populates="trade",
        foreign_keys="TradeVersion.trade_id",
        order_by="TradeVersion.last_modified",
    )


class TradeVersion(TemporalVersionMixin, Base):
    __tablename__ = "trade_versions"
    __table_args__ = (
        version_primary_key("trade_id"),
        CheckConstraint(
            "parent_trade_id IS DISTINCT FROM trade_id",
            name="parent_not_self",
        ),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        Index("ix_trade_versions_parent_trade_id", "parent_trade_id"),
    )

    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="KNX-XML Trade_t/@Name. Darf projektweit kollidieren.",
    )
    number: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=True,
    )

    trade: Mapped[Trade] = relationship(
        back_populates="versions",
        foreign_keys=[trade_id],
    )
    parent_trade: Mapped[Trade | None] = relationship(
        foreign_keys=[parent_trade_id],
    )


class TradeDevice(TemporalVersionMixin, Base):
    """Temporale Zuordnung Gewerk ↔ Gerät (DeviceInstanceRef).

    Unlink = neue Zeile mit ``linked=false``. Keine Devicespalte assigned_trade.
    """

    __tablename__ = "trade_devices"
    __table_args__ = (
        version_primary_key("trade_id", "device_id"),
        Index("ix_trade_devices_device_id", "device_id"),
    )

    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    linked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="false = Zuordnung aufgehoben ab diesem last_modified.",
    )
