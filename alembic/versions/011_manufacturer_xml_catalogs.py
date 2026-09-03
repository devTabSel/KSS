"""Manufacturer-XML catalogs; drop device_versions order_number/manufacturer

Revision ID: 011_manufacturer_xml_catalogs
Revises: 010_group_addresses_rename
Create Date: 2026-09-03

Global current-state catalogs from manufacturer XML (Hardware, Product,
Hardware2Program, ApplicationProgram, ComObject, ComObjectRef). No
installation_id, no master_data_id, not temporal.

device_versions: drop order_number/manufacturer (now on master_products);
add hardware_program_ref; application_program_ref comment is ApplicationProgram
@Id only.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_manufacturer_xml_catalogs"
down_revision: Union[str, Sequence[str], None] = "010_group_addresses_rename"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID_TYPE = postgresql.UUID(as_uuid=True)

OLD_APPLICATION_PROGRAM_REF_COMMENT = (
    "Kategorie 3. Hardware2Program / ApplicationProgram."
)
NEW_APPLICATION_PROGRAM_REF_COMMENT = (
    "Kategorie 3. ApplicationProgram @Id (M-*_A-*)."
)
HARDWARE_PROGRAM_REF_COMMENT = "Kategorie 3. Hardware2Program @Id."


def upgrade() -> None:
    op.create_table(
        "master_hardware",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column(
            "knx_id",
            sa.Text(),
            nullable=False,
            comment="Hardware @Id, z. B. M-00A6_H-00000026-1.",
        ),
        sa.Column("name", sa.Text(), nullable=True, comment="Hardware @Name."),
        sa.Column(
            "manufacturer_knx_id",
            sa.Text(),
            nullable=False,
            comment="Manufacturer @Id, z. B. M-00A6.",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_hardware"),
        sa.UniqueConstraint("knx_id", name="uq_master_hardware_knx_id"),
    )
    op.create_table(
        "master_application_programs",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column(
            "knx_id",
            sa.Text(),
            nullable=False,
            comment="ApplicationProgram @Id, z. B. M-00A6_A-0026-10-39D6.",
        ),
        sa.Column(
            "manufacturer_knx_id",
            sa.Text(),
            nullable=False,
            comment="Manufacturer @Id, z. B. M-00A6.",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_application_programs"),
        sa.UniqueConstraint("knx_id", name="uq_master_application_programs_knx_id"),
    )
    op.create_table(
        "master_products",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column(
            "knx_id",
            sa.Text(),
            nullable=False,
            comment="Product @Id = Device product_ref, z. B. M-00A6_H-00000026-1_P-1173.",
        ),
        sa.Column(
            "hardware_knx_id",
            sa.Text(),
            nullable=False,
            comment="Parent Hardware @Id.",
        ),
        sa.Column("text", sa.Text(), nullable=True, comment="Product @Text."),
        sa.Column(
            "order_number",
            sa.Text(),
            nullable=True,
            comment="Product @OrderNumber.",
        ),
        sa.Column(
            "manufacturer",
            sa.Text(),
            nullable=True,
            comment=(
                "Display-Name wie bisher Device.manufacturer "
                "(Parser manufacturer_name)."
            ),
        ),
        sa.ForeignKeyConstraint(
            ["hardware_knx_id"],
            ["master_hardware.knx_id"],
            name="fk_master_products_hardware_knx_id_master_hardware",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_products"),
        sa.UniqueConstraint("knx_id", name="uq_master_products_knx_id"),
    )
    op.create_table(
        "master_hardware2programs",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column(
            "knx_id",
            sa.Text(),
            nullable=False,
            comment=(
                "Hardware2Program @Id, z. B. M-00A6_H-00000026-1_HP-0026-10-39D6."
            ),
        ),
        sa.Column(
            "hardware_knx_id",
            sa.Text(),
            nullable=False,
            comment="Parent Hardware @Id.",
        ),
        sa.Column(
            "application_program_knx_id",
            sa.Text(),
            nullable=False,
            comment="ApplicationProgram @Id, z. B. M-00A6_A-0026-10-39D6.",
        ),
        sa.ForeignKeyConstraint(
            ["hardware_knx_id"],
            ["master_hardware.knx_id"],
            name="fk_master_hardware2programs_hardware_knx_id_master_hardware",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_hardware2programs"),
        sa.UniqueConstraint("knx_id", name="uq_master_hardware2programs_knx_id"),
    )
    op.create_table(
        "master_application_comm_objects",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("application_program_id", UUID_TYPE, nullable=False),
        sa.Column(
            "knx_id",
            sa.Text(),
            nullable=False,
            comment="Suffix nach ApplicationProgram-Id, z. B. O-2.",
        ),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column(
            "function_text",
            sa.Text(),
            nullable=True,
            comment="ComObject @FunctionText.",
        ),
        sa.Column(
            "object_size",
            sa.Text(),
            nullable=True,
            comment="ComObject @ObjectSize, z. B. 1 Bit.",
        ),
        sa.Column(
            "datapoint_type_ref",
            sa.Text(),
            nullable=True,
            comment="roh @DatapointType, z. B. DPST-10-1.",
        ),
        sa.ForeignKeyConstraint(
            ["application_program_id"],
            ["master_application_programs.id"],
            name="fk_master_application_comm_objects_program_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_application_comm_objects"),
        sa.UniqueConstraint(
            "application_program_id",
            "knx_id",
            name="uq_master_application_comm_objects_program_knx_id",
        ),
    )
    op.create_index(
        "ix_master_application_comm_objects_application_program_id",
        "master_application_comm_objects",
        ["application_program_id"],
    )
    op.create_table(
        "master_application_comm_object_refs",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("application_program_id", UUID_TYPE, nullable=False),
        sa.Column(
            "comm_object_id",
            UUID_TYPE,
            nullable=True,
            comment="Parent-CO; NULL wenn in derselben Datei fehlend.",
        ),
        sa.Column(
            "knx_id",
            sa.Text(),
            nullable=False,
            comment="Suffix O-2_R-1.",
        ),
        sa.Column(
            "function_text",
            sa.Text(),
            nullable=True,
            comment="Override @FunctionText.",
        ),
        sa.Column(
            "object_size",
            sa.Text(),
            nullable=True,
            comment="Override @ObjectSize.",
        ),
        sa.Column(
            "datapoint_type_ref",
            sa.Text(),
            nullable=True,
            comment="Override @DatapointType.",
        ),
        sa.Column("name", sa.Text(), nullable=True, comment="Override @Name."),
        sa.Column("text", sa.Text(), nullable=True, comment="Override @Text."),
        sa.ForeignKeyConstraint(
            ["application_program_id"],
            ["master_application_programs.id"],
            name="fk_master_application_comm_object_refs_program_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["comm_object_id"],
            ["master_application_comm_objects.id"],
            name="fk_master_application_comm_object_refs_comm_object_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_master_application_comm_object_refs"
        ),
        sa.UniqueConstraint(
            "application_program_id",
            "knx_id",
            name="uq_master_application_comm_object_refs_program_knx_id",
        ),
    )
    op.create_index(
        "ix_master_application_comm_object_refs_application_program_id",
        "master_application_comm_object_refs",
        ["application_program_id"],
    )
    op.create_index(
        "ix_master_application_comm_object_refs_comm_object_id",
        "master_application_comm_object_refs",
        ["comm_object_id"],
    )

    op.drop_column("device_versions", "order_number")
    op.drop_column("device_versions", "manufacturer")
    op.add_column(
        "device_versions",
        sa.Column(
            "hardware_program_ref",
            sa.Text(),
            nullable=True,
            comment=HARDWARE_PROGRAM_REF_COMMENT,
        ),
    )
    op.alter_column(
        "device_versions",
        "application_program_ref",
        existing_type=sa.Text(),
        existing_nullable=True,
        comment=NEW_APPLICATION_PROGRAM_REF_COMMENT,
        existing_comment=OLD_APPLICATION_PROGRAM_REF_COMMENT,
    )


def downgrade() -> None:
    op.alter_column(
        "device_versions",
        "application_program_ref",
        existing_type=sa.Text(),
        existing_nullable=True,
        comment=OLD_APPLICATION_PROGRAM_REF_COMMENT,
        existing_comment=NEW_APPLICATION_PROGRAM_REF_COMMENT,
    )
    op.drop_column("device_versions", "hardware_program_ref")
    op.add_column(
        "device_versions",
        sa.Column("manufacturer", sa.Text(), nullable=True),
    )
    op.add_column(
        "device_versions",
        sa.Column("order_number", sa.Text(), nullable=True),
    )

    op.drop_index(
        "ix_master_application_comm_object_refs_comm_object_id",
        table_name="master_application_comm_object_refs",
    )
    op.drop_index(
        "ix_master_application_comm_object_refs_application_program_id",
        table_name="master_application_comm_object_refs",
    )
    op.drop_table("master_application_comm_object_refs")
    op.drop_index(
        "ix_master_application_comm_objects_application_program_id",
        table_name="master_application_comm_objects",
    )
    op.drop_table("master_application_comm_objects")
    op.drop_table("master_hardware2programs")
    op.drop_table("master_products")
    op.drop_table("master_application_programs")
    op.drop_table("master_hardware")
