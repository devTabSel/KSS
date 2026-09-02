"""temporal last_modified PK, last_import, bus bindings

Revision ID: 003_temporal_last_modified_bus_bindings
Revises: 002_installation_project_attrs
Create Date: 2026-09-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_temporal_lm_bus"
down_revision: Union[str, Sequence[str], None] = "002_installation_project_attrs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VERSION_TABLES: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("installation_versions", ("installation_id",), True),
    ("area_versions", ("area_id",), False),
    ("line_versions", ("line_id",), False),
    ("segment_versions", ("segment_id",), False),
    ("location_versions", ("location_id",), False),
    ("function_versions", ("function_id",), False),
    ("function_datapoints", ("function_id", "datapoint_id"), False),
    ("group_range_versions", ("group_range_id",), False),
    ("datapoint_versions", ("datapoint_id",), True),
    ("device_versions", ("device_id",), True),
    ("device_channel_versions", ("channel_id",), False),
    ("device_folder_versions", ("folder_id",), False),
    ("comm_object_versions", ("comm_object_id",), False),
    ("comm_object_datapoints", ("comm_object_id", "datapoint_id"), False),
    ("trade_versions", ("trade_id",), False),
    ("trade_devices", ("trade_id", "device_id"), False),
)


def _migrate_version_table(
    table: str,
    entity_columns: tuple[str, ...],
    has_last_modified: bool,
) -> None:
    pk_name = f"pk_{table}"
    if not has_last_modified:
        op.add_column(
            table,
            sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET last_modified = _since WHERE last_modified IS NULL"
            )
        )
    else:
        op.execute(
            sa.text(
                f"UPDATE {table} SET last_modified = _since "
                f"WHERE last_modified IS NULL"
            )
        )
    op.drop_constraint(pk_name, table, type_="primary")
    op.drop_column(table, "_since")
    op.drop_column(table, "_observable_since")
    op.alter_column(table, "last_modified", nullable=False)
    op.create_primary_key(pk_name, table, [*entity_columns, "last_modified"])


def _revert_version_table(
    table: str,
    entity_columns: tuple[str, ...],
    had_last_modified: bool,
) -> None:
    pk_name = f"pk_{table}"
    op.add_column(
        table,
        sa.Column("_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        table,
        sa.Column("_observable_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            f"UPDATE {table} SET _since = last_modified, "
            f"_observable_since = last_modified"
        )
    )
    op.drop_constraint(pk_name, table, type_="primary")
    if had_last_modified:
        op.alter_column(table, "last_modified", nullable=True)
    else:
        op.drop_column(table, "last_modified")
    op.alter_column(table, "_since", nullable=False)
    op.alter_column(table, "_observable_since", nullable=False)
    op.create_primary_key(pk_name, table, [*entity_columns, "_since"])


def upgrade() -> None:
    op.add_column(
        "installations",
        sa.Column(
            "last_import",
            sa.DateTime(timezone=True),
            nullable=True,
            comment=(
                "KSS Kategorie 3. UTC-Zeitpunkt des letzten PATCH-Ingest "
                "(Import-Uhr, nicht ETS-LastModified)."
            ),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE installations i
            SET last_import = COALESCE(
                (
                    SELECT max(iv._observable_since)
                    FROM installation_versions iv
                    WHERE iv.installation_id = i.id
                ),
                now()
            )
            """
        )
    )
    op.alter_column("installations", "last_import", nullable=False)

    for table, entity_columns, has_last_modified in VERSION_TABLES:
        _migrate_version_table(table, entity_columns, has_last_modified)

    op.add_column(
        "device_versions",
        sa.Column(
            "individual_address_loaded",
            sa.Boolean(),
            nullable=True,
            comment="Kategorie 3. IndividualAddressLoaded.",
        ),
    )
    op.add_column(
        "device_versions",
        sa.Column(
            "application_program_loaded",
            sa.Boolean(),
            nullable=True,
            comment="Kategorie 3. ApplicationProgramLoaded.",
        ),
    )
    op.add_column(
        "device_versions",
        sa.Column(
            "parameters_loaded",
            sa.Boolean(),
            nullable=True,
            comment="Kategorie 3. ParametersLoaded.",
        ),
    )
    op.add_column(
        "device_versions",
        sa.Column(
            "medium_config_loaded",
            sa.Boolean(),
            nullable=True,
            comment="Kategorie 3. MediumConfigLoaded.",
        ),
    )

    op.create_table(
        "bus_pa_bindings",
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "individual_address",
            sa.Text(),
            nullable=False,
            comment="3API-Punktnotation, z. B. 1.0.248.",
        ),
        sa.Column(
            "last_downloaded",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="BUS-Wirksamkeit; Sentinel 0001-01-01 nie speichern.",
        ),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(individual_address)) > 0",
            name=op.f("ck_bus_pa_bindings_individual_address"),
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_bus_pa_bindings_device_id_devices"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["installation_id"],
            ["installations.id"],
            name=op.f("fk_bus_pa_bindings_installation_id_installations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "installation_id",
            "individual_address",
            "last_downloaded",
            name=op.f("pk_bus_pa_bindings"),
        ),
    )
    op.create_index(
        "ix_bus_pa_bindings_lookup",
        "bus_pa_bindings",
        ["installation_id", "individual_address", "last_downloaded"],
        unique=False,
    )

    op.create_table(
        "bus_ga_bindings",
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "group_address",
            sa.Integer(),
            nullable=False,
            comment="16-Bit bus-wirksamer Integer zum Download-Stand.",
        ),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_downloaded", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "group_address >= 0 AND group_address <= 65535",
            name=op.f("ck_bus_ga_bindings_group_address"),
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_bus_ga_bindings_device_id_devices"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["installation_id"],
            ["installations.id"],
            name=op.f("fk_bus_ga_bindings_installation_id_installations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "installation_id",
            "group_address",
            "device_id",
            "last_downloaded",
            name=op.f("pk_bus_ga_bindings"),
        ),
    )
    op.create_index(
        "ix_bus_ga_bindings_lookup",
        "bus_ga_bindings",
        ["installation_id", "group_address", "last_downloaded"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bus_ga_bindings_lookup", table_name="bus_ga_bindings")
    op.drop_table("bus_ga_bindings")
    op.drop_index("ix_bus_pa_bindings_lookup", table_name="bus_pa_bindings")
    op.drop_table("bus_pa_bindings")

    op.drop_column("device_versions", "medium_config_loaded")
    op.drop_column("device_versions", "parameters_loaded")
    op.drop_column("device_versions", "application_program_loaded")
    op.drop_column("device_versions", "individual_address_loaded")

    for table, entity_columns, had_last_modified in reversed(VERSION_TABLES):
        _revert_version_table(table, entity_columns, had_last_modified)

    op.drop_column("installations", "last_import")
