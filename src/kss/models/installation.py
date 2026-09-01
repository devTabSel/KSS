"""Paket Installation: 3API Installation + knxproj-Identität + knx_master-Katalog.

Schema-Quellen:
- 3API Installation* / Datafield*
- knxproj ProjectInformation, Installation, MasterData
- KIM core:Installation; core:state = CompletionStatus = 3API state
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kss.models.base import Base
from kss.models.constants import (
    COMPLETION_STATUS_SQL,
    DATAFIELD_KIND_SQL,
    GROUP_ADDRESS_STYLE_SQL,
)
from kss.models.temporal import TemporalSinceMixin, since_primary_key


class Installation(Base):
    """Stabile Identität einer Installation (3API ``data.id``).

    JSON:API ``type`` ist konstant ``installation`` und wird nicht persistiert.
    ``group_address_style`` ändert sich während der Projektlebensdauer nicht
    und liegt deshalb auf der Identität, nicht auf der Version.
    """

    __tablename__ = "installations"
    __table_args__ = (
        UniqueConstraint("project_guid", name="uq_installations_project_guid"),
        UniqueConstraint("ets_id", name="uq_installations_ets_id"),
        CheckConstraint(GROUP_ADDRESS_STYLE_SQL, name="group_address_style"),
        Index("ix_installations_knx_project_id", "knx_project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API InstallationTypeAndId.id (uuid).",
    )
    ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Kategorie 3. knxproj Project/@Id + InstallationIndex, z. B. "
            "P-040E-0. TTL prj:P-040E-0."
        ),
    )
    project_guid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment=(
            "Kategorie 3. ProjectInformation/@Guid = TTL-Namespace "
            "http://iot.knx.org/{Guid}#."
        ),
    )
    knx_project_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Project/@Id ohne InstallationIndex, z. B. P-040E.",
    )
    installation_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Kategorie 3. Installation-Index im knxproj (meist 0).",
    )
    group_address_style: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Kategorie 3. ProjectInformation/@GroupAddressStyle. "
            "ThreeLevel | TwoLevel | Free. Nicht historisiert."
        ),
    )

    versions: Mapped[list[InstallationVersion]] = relationship(
        back_populates="installation",
        order_by="InstallationVersion._since",
    )
    subscriptions: Mapped[list[InstallationSubscription]] = relationship(
        back_populates="installation",
    )


class InstallationVersion(TemporalSinceMixin, Base):
    """Gültigkeitsversion der semantischen Installationsattribute.

    3API ``attributes.state`` und knxproj/KIM CompletionStatus liegen in
    derselben Spalte ``completion_status``.
    """

    __tablename__ = "installation_versions"
    __table_args__ = (
        since_primary_key("installation_id"),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
    )

    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK zur stabilen Installations-Identität.",
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "3API attributes.title. Quelle knxproj: ProjectInformation/@Name "
            "(Installation/@Name oft leer). TTL dct:title."
        ),
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API attributes.comment (nullable). RTF möglich.",
    )
    contract_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API attributes.contractNumber (nullable).",
    )
    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="3API attributes.lastModified / ProjectInformation/@LastModified.",
    )
    project_installation_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API attributes.projectInstallationNumber (nullable).",
    )
    completion_status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Eine Spalte für 3API attributes.state, knxproj "
            "CompletionStatus und TTL core:state. XML-Omit = Undefined."
        ),
    )
    type_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API item.meta.typedescription (uri, optional).",
    )
    master_data_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Kategorie 3. knx_master MasterData/@Version.",
    )

    installation: Mapped[Installation] = relationship(back_populates="versions")


class InstallationSubscription(Base):
    """Aktuelle Zuordnung Installation ↔ Subscription (nicht historisiert)."""

    __tablename__ = "installation_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "subscription_id",
            name="uq_installation_subscriptions_pair",
        ),
        Index("ix_installation_subscriptions_installation_id", "installation_id"),
        Index("ix_installation_subscriptions_subscription_id", "subscription_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
        comment="3API installation id.",
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="3API subscription id (Subscription-Entität nicht in diesem Modell).",
    )

    installation: Mapped[Installation] = relationship(back_populates="subscriptions")


class MasterDatapointType(Base):
    """knx_master DatapointType (DPT-*), current-state, installationsbezogen."""

    __tablename__ = "master_datapoint_types"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_master_datapoint_types_installation_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(Text, nullable=False, comment="z. B. DPT-1.")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_in_bit: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MasterDatapointSubtype(Base):
    """knx_master DatapointSubtype (DPST-*), current-state."""

    __tablename__ = "master_datapoint_subtypes"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_master_datapoint_subtypes_installation_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(Text, nullable=False, comment="z. B. DPST-1-2.")
    datapoint_type_ets_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)


class Datafield(Base):
    """3API ``datafield`` = knx_master Format-Feld (z. B. DPST-1-2_F-1).

    Current-state (Katalog). Runtime-``value`` wird nicht persistiert.
    Enum/Unit/Min/Max leben hier, nicht auf der Gruppenadresse.
    """

    __tablename__ = "datafields"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_datafields_installation_ets_id",
        ),
        CheckConstraint(DATAFIELD_KIND_SQL, name="kind"),
        Index("ix_datafields_installation_id", "installation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API DatafieldTypeAndId.id (uuid).",
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Kategorie 3. Format-Id, z. B. DPST-1-2_F-1.",
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="3API attributes.title.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    datapoint_subtype_ets_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="DPST-*, dem dieses Format-Feld zugeordnet ist.",
    )
    kind: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3API oneOf: enum | numbered | datetime | string.",
    )
    enum_value_map: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="3API attributes.enumValueMap.",
    )
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimum: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    maximum: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    resolution: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    integer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charset: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MasterFunctionType(Base):
    """knx_master FunctionType (FT-*), current-state."""

    __tablename__ = "master_function_types"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_master_function_types_installation_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(Text, nullable=False, comment="z. B. FT-0.")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)


class MasterDatapointRole(Base):
    """knx_master DatapointRole (DR-*), current-state."""

    __tablename__ = "master_datapoint_roles"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_master_datapoint_roles_installation_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(Text, nullable=False, comment="z. B. DR-1.")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)


class MasterSpaceUsage(Base):
    """knx_master SpaceUsage (SU-*). ETS 6.4 kann zusätzlich tag:bedroom nutzen."""

    __tablename__ = "master_space_usages"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_master_space_usages_installation_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(Text, nullable=False, comment="z. B. SU-2.")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)


class MasterMediumType(Base):
    """knx_master MediumType (MT-*), current-state."""

    __tablename__ = "master_medium_types"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "ets_id",
            name="uq_master_medium_types_installation_ets_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("installations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ets_id: Mapped[str] = mapped_column(Text, nullable=False, comment="z. B. MT-0.")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
