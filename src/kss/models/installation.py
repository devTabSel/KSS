"""Paket Installation: 3API Installation + knxproj-Identität.

knx_master-Kataloge liegen in ``kss.models.master``.
Zeiger: ``installation_versions.master_data_version``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kss.models.base import Base
from kss.models.constants import (
    COMPLETION_STATUS_SQL,
    GROUP_ADDRESS_STYLE_SQL,
    PROJECT_TYPE_SQL,
)
from kss.models.temporal import TemporalVersionMixin, version_primary_key


class Installation(Base):
    """Stabile Identität einer Installation (3API ``data.id``).

    JSON:API ``type`` ist konstant ``installation`` und wird nicht persistiert.
    ``group_address_style`` liegt auf der Version.
    """

    __tablename__ = "installations"
    __table_args__ = (
        UniqueConstraint("project_guid", name="uq_installations_project_guid"),
        UniqueConstraint("ets_id", name="uq_installations_ets_id"),
        CheckConstraint(
            "language_code IS NULL OR char_length(btrim(language_code)) >= 2",
            name="language_code",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API InstallationTypeAndId.id (uuid).",
    )
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Kategorie 3. knxproj Project/@Id + InstallationIndex, z. B. "
            "P-040E-0. TTL prj:P-040E-0."
        ),
    )
    project_guid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment=(
            "Kategorie 3. ProjectInformation/@Guid = TTL-Namespace "
            "http://iot.knx.org/{Guid}#."
        ),
    )
    last_import: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "KSS Kategorie 3. UTC-Zeitpunkt des letzten PATCH-Ingest "
            "(Import-Uhr, nicht ETS-LastModified)."
        ),
    )
    project_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Kategorie 3. ProjectInformation/@ProjectStart. Identität.",
    )
    language_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Projekt-Sprache auf der Identität.",
    )

    versions: Mapped[list[InstallationVersion]] = relationship(
        back_populates="installation",
        order_by="InstallationVersion.last_modified",
    )
    subscriptions: Mapped[list[InstallationSubscription]] = relationship(
        back_populates="installation",
    )


class InstallationVersion(TemporalVersionMixin, Base):
    """Gültigkeitsversion der semantischen Installationsattribute.

    3API ``attributes.state`` und knxproj/KIM CompletionStatus liegen in
    derselben Spalte ``completion_status``.
    """

    __tablename__ = "installation_versions"
    __table_args__ = (
        version_primary_key("installation_id"),
        CheckConstraint(COMPLETION_STATUS_SQL, name="completion_status"),
        CheckConstraint(PROJECT_TYPE_SQL, name="project_type"),
        CheckConstraint(GROUP_ADDRESS_STYLE_SQL, name="group_address_style"),
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
        comment=(
            "3API attributes.comment (nullable). knxproj "
            "ProjectInformation/@Comment (xs:string, oft RTF). "
            "KIM core:comment an core:Installation."
        ),
    )
    contract_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "3API attributes.contractNumber (nullable). knxproj "
            "ProjectInformation/@ContractNumber. KIM knx:contractNumber."
        ),
    )
    project_installation_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "3API attributes.projectInstallationNumber (nullable). knxproj "
            "ProjectInformation/@ProjectNumber (ETS Projektnummer). "
            "KIM knx:projectInstallationNumber. Eine Spalte für alle drei Namen."
        ),
    )
    completion_status: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Eine Spalte für 3API attributes.state, knxproj "
            "CompletionStatus und TTL core:state. XML-Omit = Undefined."
        ),
    )
    project_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Kategorie 3. knxproj ProjectInformation/@ProjectType. "
            "XSD 23 ProjectType_t (XML-Token, z. B. Family House). "
            "Anzeigenamen sprachabhängig in master_project_types."
        ),
    )
    master_data_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Kategorie 3. knx_master MasterData/@Version.",
    )
    schema_version: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. KNX/@SchemaVersion, Namespace project/23.",
    )
    created_by: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. KNX/@CreatedBy.",
    )
    tool_version: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. KNX/@ToolVersion.",
    )
    ip_routing_backbone_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Installation/@IPRoutingBackboneKey (KNX IP Secure).",
    )
    bcu_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Kategorie 3. Installation/@BCUKey.",
    )
    group_address_style: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Kategorie 3. ProjectInformation/@GroupAddressStyle. "
            "ThreeLevel | TwoLevel | Free. Anzeige der 16-Bit-GA."
        ),
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
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
