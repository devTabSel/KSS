"""knx_master- und Hersteller-XML-Kataloge (current-state).

knx_master: Unique Snapshot ``(MasterData/@Id, @Version)`` = ``MD-1`` + Version.
Katalogzeilen Unique ``(master_data_id, knx_id)``. Inline-Text = Default en-US;
andere Sprachen in ``master_translations``.

Hersteller-XML (Hardware/Product/Hardware2Program/ApplicationProgram/ComObject):
global, Unique ``knx_id`` bzw. ``(application_program_id, knx_id)``.
Kein ``installation_id``, kein ``master_data_id``, nicht temporal.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from kss.models.base import Base
from kss.models.constants import (
    DATAFIELD_KIND_SQL,
    LANGUAGE_CODE_SQL,
    MASTER_PROJECT_TYPE_ETS_ID_SQL,
)


class MasterData(Base):
    """knx_master MasterData-Snapshot. Nicht temporal."""

    __tablename__ = "master_data"
    __table_args__ = (
        UniqueConstraint("knx_id", "version", name="uq_master_data_knx_id_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="MasterData/@Id, z. B. MD-1.",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="MasterData/@Version.",
    )


class MasterTranslation(Base):
    """Sprachlabel zu einem Katalog-RefId (nicht en-US-Default der Entity)."""

    __tablename__ = "master_translations"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            "language_code",
            "attribute_name",
            name="uq_master_translations_key",
        ),
        CheckConstraint(LANGUAGE_CODE_SQL, name="language_code"),
        Index("ix_master_translations_master_data_id", "master_data_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="RefId: DPT-1, M-0083, FT-0, FP-1_DR-1, DPST-1-2_F-1, …",
    )
    language_code: Mapped[str] = mapped_column(Text, nullable=False)
    attribute_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Translation/@AttributeName: Text, Name, …",
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)


class MasterDatapointType(Base):
    """knx_master DatapointType (DPT-*)."""

    __tablename__ = "master_datapoint_types"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_datapoint_types_master_data_knx_id",
        ),
        Index("ix_master_datapoint_types_master_data_id", "master_data_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="DPT-1.")
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Default @Text (en-US).")
    code: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Name, z. B. 1.xxx.")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="@Number.")
    size_in_bit: Mapped[int] = mapped_column(Integer, nullable=False)


class MasterDatapointSubtype(Base):
    """knx_master DatapointSubtype (DPST-*)."""

    __tablename__ = "master_datapoint_subtypes"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_datapoint_subtypes_master_data_knx_id",
        ),
        Index("ix_master_datapoint_subtypes_master_data_id", "master_data_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="DPST-1-2.")
    datapoint_type_knx_id: Mapped[str] = mapped_column(
        Text, nullable=False, comment="DPT-1."
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Default @Text.")
    code: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="@Name, z. B. DPT_Switch."
    )
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="@Default.")


class Datafield(Base):
    """3API datafield = knx_master Format-Feld (DPST-1-2_F-1)."""

    __tablename__ = "datafields"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_datafields_master_data_knx_id",
        ),
        CheckConstraint(DATAFIELD_KIND_SQL, name="kind"),
        Index("ix_datafields_master_data_id", "master_data_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="3API DatafieldTypeAndId.id (uuid).",
    )
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Format-Id, z. B. DPST-1-2_F-1."
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, comment="3API attributes.title.")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    datapoint_subtype_knx_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="3API oneOf: enum | numbered | datetime | string."
    )
    enum_value_map: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimum: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    maximum: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    resolution: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    integer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charset: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MasterFunctionType(Base):
    """knx_master FunctionType (FT-*)."""

    __tablename__ = "master_function_types"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_function_types_master_data_knx_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="FT-0.")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Text.")
    status: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="z. B. deprecated an FT-2."
    )


class MasterDatapointRole(Base):
    """knx_master DatapointRole (DR-*)."""

    __tablename__ = "master_datapoint_roles"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_datapoint_roles_master_data_knx_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="DR-1.")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Name.")


class MasterSpaceUsage(Base):
    """knx_master SpaceUsage (SU-*). Kein tag:*."""

    __tablename__ = "master_space_usages"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_space_usages_master_data_knx_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="SU-12.")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Text.")


class MasterMediumType(Base):
    """knx_master MediumType (MT-*)."""

    __tablename__ = "master_medium_types"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_medium_types_master_data_knx_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="MT-0.")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Name TP.")
    text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="@Text.")
    domain_address_length: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MasterFunctionPoint(Base):
    """knx_master FunctionPoint (FP-1_DR-1)."""

    __tablename__ = "master_function_points"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_function_points_master_data_knx_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False)
    function_type_knx_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_knx_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    datapoint_subtype_knx_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    characteristics: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)


class MasterManufacturer(Base):
    """knx_master Manufacturers only (M-0083). Nicht Hersteller-XML."""

    __tablename__ = "master_manufacturers"
    __table_args__ = (
        UniqueConstraint(
            "master_data_id",
            "knx_id",
            name="uq_master_manufacturers_master_data_knx_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    master_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_data.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(Text, nullable=False, comment="M-0083.")
    knx_manufacturer_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="@KnxManufacturerId."
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Inline @Name.")
    default_language_code: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Produktdaten-Default, nicht Name-Locale."
    )


class MasterProjectType(Base):
    """Sprachabhängiger ProjectType-Katalog (XSD-Token, kein master_data_id)."""

    __tablename__ = "master_project_types"
    __table_args__ = (
        UniqueConstraint(
            "ets_id",
            "language_code",
            name="uq_master_project_types_ets_id_language",
        ),
        CheckConstraint(MASTER_PROJECT_TYPE_ETS_ID_SQL, name="ets_id"),
        CheckConstraint(LANGUAGE_CODE_SQL, name="language_code"),
        CheckConstraint("char_length(btrim(name)) > 0", name="name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    ets_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="XSD 23 ProjectType_t, z. B. Airport.",
    )
    language_code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)


class MasterHardware(Base):
    """Hersteller-XML Hardware. Global, current-state."""

    __tablename__ = "master_hardware"
    __table_args__ = (
        UniqueConstraint("knx_id", name="uq_master_hardware_knx_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Hardware @Id, z. B. M-00A6_H-00000026-1.",
    )
    name: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Hardware @Name."
    )
    manufacturer_knx_id: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Manufacturer @Id, z. B. M-00A6."
    )


class MasterProduct(Base):
    """Hersteller-XML Product. Global, current-state.

    Trägt ``order_number`` / ``manufacturer`` (Display-Name), die zuvor auf
    ``device_versions`` lagen.
    """

    __tablename__ = "master_products"
    __table_args__ = (
        UniqueConstraint("knx_id", name="uq_master_products_knx_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Product @Id = Device product_ref, z. B. M-00A6_H-00000026-1_P-1173.",
    )
    hardware_knx_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("master_hardware.knx_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Parent Hardware @Id.",
    )
    text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Product @Text."
    )
    order_number: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Product @OrderNumber."
    )
    manufacturer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Display-Name wie bisher Device.manufacturer (Parser manufacturer_name).",
    )


class MasterHardware2Program(Base):
    """Hersteller-XML Hardware2Program. Global, current-state."""

    __tablename__ = "master_hardware2programs"
    __table_args__ = (
        UniqueConstraint("knx_id", name="uq_master_hardware2programs_knx_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Hardware2Program @Id, z. B. M-00A6_H-00000026-1_HP-0026-10-39D6.",
    )
    hardware_knx_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("master_hardware.knx_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Parent Hardware @Id.",
    )
    application_program_knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="ApplicationProgram @Id, z. B. M-00A6_A-0026-10-39D6.",
    )


class MasterApplicationProgram(Base):
    """Hersteller-XML ApplicationProgram. Global, current-state."""

    __tablename__ = "master_application_programs"
    __table_args__ = (
        UniqueConstraint("knx_id", name="uq_master_application_programs_knx_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="ApplicationProgram @Id, z. B. M-00A6_A-0026-10-39D6.",
    )
    manufacturer_knx_id: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Manufacturer @Id, z. B. M-00A6."
    )


class MasterApplicationCommObject(Base):
    """ComObject der ApplicationProgram (Katalog, nicht Device-Instanz)."""

    __tablename__ = "master_application_comm_objects"
    __table_args__ = (
        UniqueConstraint(
            "application_program_id",
            "knx_id",
            name="uq_master_application_comm_objects_program_knx_id",
        ),
        Index(
            "ix_master_application_comm_objects_application_program_id",
            "application_program_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    application_program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "master_application_programs.id",
            ondelete="RESTRICT",
            name="fk_master_application_comm_objects_program_id",
        ),
        nullable=False,
    )
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Suffix nach ApplicationProgram-Id, z. B. O-2.",
    )
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    function_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="ComObject @FunctionText."
    )
    object_size: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="ComObject @ObjectSize, z. B. 1 Bit."
    )
    datapoint_type_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="roh @DatapointType, z. B. DPST-10-1."
    )


class MasterApplicationCommObjectRef(Base):
    """ComObjectRef (Instanz-RefId O-…_R-…). Overrides nullable."""

    __tablename__ = "master_application_comm_object_refs"
    __table_args__ = (
        UniqueConstraint(
            "application_program_id",
            "knx_id",
            name="uq_master_application_comm_object_refs_program_knx_id",
        ),
        Index(
            "ix_master_application_comm_object_refs_application_program_id",
            "application_program_id",
        ),
        Index(
            "ix_master_application_comm_object_refs_comm_object_id",
            "comm_object_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    application_program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "master_application_programs.id",
            ondelete="RESTRICT",
            name="fk_master_application_comm_object_refs_program_id",
        ),
        nullable=False,
    )
    comm_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "master_application_comm_objects.id",
            ondelete="RESTRICT",
            name="fk_master_application_comm_object_refs_comm_object_id",
        ),
        nullable=True,
        comment="Parent-CO; NULL wenn in derselben Datei fehlend.",
    )
    knx_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Suffix O-2_R-1.",
    )
    function_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Override @FunctionText."
    )
    object_size: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Override @ObjectSize."
    )
    datapoint_type_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Override @DatapointType."
    )
    name: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Override @Name."
    )
    text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Override @Text."
    )
