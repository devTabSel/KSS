"""KSS Modellierung Feldlisten (global master, identity/version deltas)

Revision ID: 006_modellierung_feldlisten
Revises: 005_channel_description
Create Date: 2026-09-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from kss.models.constants import COMPLETION_STATUS_SQL, GROUP_ADDRESS_STYLE_SQL, LANGUAGE_CODE_SQL

revision: str = "006_modellierung_feldlisten"
down_revision: Union[str, Sequence[str], None] = "005_channel_description"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADDRESS_SQL = "address >= 0 AND address <= 15"
UUID_TYPE = postgresql.UUID(as_uuid=True)

CATALOGS = (
    "master_datapoint_types",
    "master_datapoint_subtypes",
    "datafields",
    "master_function_types",
    "master_datapoint_roles",
    "master_space_usages",
    "master_medium_types",
)


def _drop_fk(table: str, column: str, referred: str) -> None:
    op.drop_constraint(
        op.f(f"fk_{table}_{column}_{referred}"),
        table,
        type_="foreignkey",
    )


def _add_completion(table: str) -> None:
    op.add_column(table, sa.Column("completion_status", sa.Text(), nullable=True))
    op.create_check_constraint("completion_status", table, COMPLETION_STATUS_SQL)


def _drop_completion(table: str) -> None:
    op.drop_constraint("completion_status", table, type_="check")
    op.drop_column(table, "completion_status")


def upgrade() -> None:
    # --- installations ---
    op.add_column(
        "installations",
        sa.Column("project_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("installations", sa.Column("language_code", sa.Text(), nullable=True))
    op.create_check_constraint(
        "language_code",
        "installations",
        "language_code IS NULL OR char_length(btrim(language_code)) >= 2",
    )
    op.execute(
        sa.text(
            "UPDATE installations SET ets_id = 'MISSING-' || id::text WHERE ets_id IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE installations SET project_guid = id WHERE project_guid IS NULL"
        )
    )
    op.alter_column("installations", "ets_id", existing_type=sa.Text(), nullable=False)
    op.alter_column("installations", "project_guid", existing_type=UUID_TYPE, nullable=False)
    op.drop_index("ix_installations_knx_project_id", table_name="installations")
    op.drop_column("installations", "knx_project_id")
    op.drop_column("installations", "installation_index")

    op.add_column(
        "installation_versions",
        sa.Column("group_address_style", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE installation_versions iv
            SET group_address_style = i.group_address_style
            FROM installations i
            WHERE iv.installation_id = i.id
            """
        )
    )
    op.create_check_constraint(
        "group_address_style",
        "installation_versions",
        GROUP_ADDRESS_STYLE_SQL,
    )
    op.drop_constraint(
        op.f("ck_installations_group_address_style"),
        "installations",
        type_="check",
    )
    op.drop_column("installations", "group_address_style")

    op.drop_column("installation_versions", "type_description")
    op.add_column("installation_versions", sa.Column("schema_version", sa.Text(), nullable=True))
    op.add_column("installation_versions", sa.Column("created_by", sa.Text(), nullable=True))
    op.add_column("installation_versions", sa.Column("tool_version", sa.Text(), nullable=True))
    op.add_column(
        "installation_versions",
        sa.Column("ip_routing_backbone_key", sa.Text(), nullable=True),
    )
    op.add_column("installation_versions", sa.Column("bcu_key", sa.Text(), nullable=True))

    op.add_column(
        "installation_subscriptions",
        sa.Column("id_uuid", UUID_TYPE, nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE installation_subscriptions
            SET id_uuid = md5(
                id::text || installation_id::text || subscription_id::text
            )::uuid
            """
        )
    )
    op.drop_constraint(
        op.f("pk_installation_subscriptions"), "installation_subscriptions", type_="primary"
    )
    op.drop_column("installation_subscriptions", "id")
    op.alter_column(
        "installation_subscriptions",
        "id_uuid",
        new_column_name="id",
        existing_type=UUID_TYPE,
        nullable=False,
    )
    op.create_primary_key(
        op.f("pk_installation_subscriptions"), "installation_subscriptions", ["id"]
    )

    # --- master_data ---
    op.create_table(
        "master_data",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("knx_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_master_data"),
        sa.UniqueConstraint("knx_id", "version", name="uq_master_data_knx_id_version"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO master_data (id, knx_id, version)
            SELECT md5('kss-master-data-md-1-' || COALESCE(v.ver, 0)::text)::uuid,
                   'MD-1', COALESCE(v.ver, 0)
            FROM (
                SELECT MAX(master_data_version) AS ver FROM installation_versions
            ) v
            """
        )
    )
    op.create_table(
        "master_translations",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("master_data_id", UUID_TYPE, nullable=False),
        sa.Column("knx_id", sa.Text(), nullable=False),
        sa.Column("language_code", sa.Text(), nullable=False),
        sa.Column("attribute_name", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint(LANGUAGE_CODE_SQL, name="ck_master_translations_language_code"),
        sa.ForeignKeyConstraint(
            ["master_data_id"],
            ["master_data.id"],
            name="fk_master_translations_master_data_id_master_data",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_translations"),
        sa.UniqueConstraint(
            "master_data_id",
            "knx_id",
            "language_code",
            "attribute_name",
            name="uq_master_translations_key",
        ),
    )
    op.create_index(
        "ix_master_translations_master_data_id",
        "master_translations",
        ["master_data_id"],
    )

    bind = "(SELECT id FROM master_data ORDER BY version DESC LIMIT 1)"
    for table in CATALOGS:
        op.add_column(table, sa.Column("master_data_id", UUID_TYPE, nullable=True))
        op.execute(sa.text(f"UPDATE {table} SET master_data_id = {bind}"))
        op.drop_constraint(f"uq_{table}_installation_ets_id", table, type_="unique")
        _drop_fk(table, "installation_id", "installations")
        op.execute(
            sa.text(
                f"""
                DELETE FROM {table} a USING {table} b
                WHERE a.master_data_id = b.master_data_id
                  AND a.ets_id = b.ets_id
                  AND a.id > b.id
                """
            )
        )
        if table == "datafields":
            op.drop_index("ix_datafields_installation_id", table_name="datafields")
        op.drop_column(table, "installation_id")
        op.alter_column(table, "ets_id", new_column_name="knx_id", existing_type=sa.Text())
        op.alter_column(table, "master_data_id", existing_type=UUID_TYPE, nullable=False)
        op.create_foreign_key(
            f"fk_{table}_master_data_id_master_data",
            table,
            "master_data",
            ["master_data_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_unique_constraint(
            f"uq_{table}_master_data_knx_id",
            table,
            ["master_data_id", "knx_id"],
        )
        op.create_index(f"ix_{table}_master_data_id", table, ["master_data_id"])

    op.add_column("master_datapoint_types", sa.Column("text", sa.Text(), nullable=True))
    op.add_column("master_datapoint_types", sa.Column("code", sa.Text(), nullable=True))
    op.add_column("master_datapoint_types", sa.Column("number", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE master_datapoint_types SET text = COALESCE(name, knx_id), "
            "size_in_bit = COALESCE(size_in_bit, 1)"
        )
    )
    op.alter_column("master_datapoint_types", "text", existing_type=sa.Text(), nullable=False)
    op.alter_column(
        "master_datapoint_types", "size_in_bit", existing_type=sa.Integer(), nullable=False
    )
    op.drop_column("master_datapoint_types", "name")

    op.add_column("master_datapoint_subtypes", sa.Column("text", sa.Text(), nullable=True))
    op.add_column("master_datapoint_subtypes", sa.Column("code", sa.Text(), nullable=True))
    op.add_column("master_datapoint_subtypes", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("master_datapoint_subtypes", sa.Column("is_default", sa.Boolean(), nullable=True))
    op.execute(sa.text("UPDATE master_datapoint_subtypes SET text = name"))
    op.execute(
        sa.text(
            "UPDATE master_datapoint_subtypes SET datapoint_type_ets_id = '' "
            "WHERE datapoint_type_ets_id IS NULL"
        )
    )
    op.alter_column(
        "master_datapoint_subtypes",
        "datapoint_type_ets_id",
        new_column_name="datapoint_type_knx_id",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("master_datapoint_subtypes", "name")

    op.alter_column(
        "datafields",
        "datapoint_subtype_ets_id",
        new_column_name="datapoint_subtype_knx_id",
        existing_type=sa.Text(),
    )

    op.add_column("master_function_types", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("master_function_types", sa.Column("text", sa.Text(), nullable=True))
    op.add_column("master_function_types", sa.Column("status", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_function_types SET text = name"))
    op.drop_column("master_function_types", "name")

    op.add_column("master_datapoint_roles", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("master_datapoint_roles", sa.Column("code", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_datapoint_roles SET code = name"))
    op.drop_column("master_datapoint_roles", "name")

    op.add_column("master_space_usages", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("master_space_usages", sa.Column("text", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_space_usages SET text = name"))
    op.drop_column("master_space_usages", "name")

    op.add_column("master_medium_types", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("master_medium_types", sa.Column("code", sa.Text(), nullable=True))
    op.add_column("master_medium_types", sa.Column("text", sa.Text(), nullable=True))
    op.add_column(
        "master_medium_types", sa.Column("domain_address_length", sa.Integer(), nullable=True)
    )
    op.execute(sa.text("UPDATE master_medium_types SET code = name"))
    op.drop_column("master_medium_types", "name")

    op.create_table(
        "master_function_points",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("master_data_id", UUID_TYPE, nullable=False),
        sa.Column("knx_id", sa.Text(), nullable=False),
        sa.Column("function_type_knx_id", sa.Text(), nullable=True),
        sa.Column("role_knx_id", sa.Text(), nullable=True),
        sa.Column("datapoint_subtype_knx_id", sa.Text(), nullable=True),
        sa.Column("characteristics", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["master_data_id"],
            ["master_data.id"],
            name="fk_master_function_points_master_data_id_master_data",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_function_points"),
        sa.UniqueConstraint(
            "master_data_id", "knx_id", name="uq_master_function_points_master_data_knx_id"
        ),
    )
    op.create_table(
        "master_manufacturers",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("master_data_id", UUID_TYPE, nullable=False),
        sa.Column("knx_id", sa.Text(), nullable=False),
        sa.Column("knx_manufacturer_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("default_language_code", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["master_data_id"],
            ["master_data.id"],
            name="fk_master_manufacturers_master_data_id_master_data",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_master_manufacturers"),
        sa.UniqueConstraint(
            "master_data_id", "knx_id", name="uq_master_manufacturers_master_data_knx_id"
        ),
    )

    op.drop_constraint(
        "uq_master_project_types_installation_ets_id_language",
        "master_project_types",
        type_="unique",
    )
    _drop_fk("master_project_types", "installation_id", "installations")
    op.drop_index("ix_master_project_types_installation_id", table_name="master_project_types")
    op.execute(
        sa.text(
            """
            DELETE FROM master_project_types a USING master_project_types b
            WHERE a.ets_id = b.ets_id AND a.language_code = b.language_code AND a.id > b.id
            """
        )
    )
    op.drop_column("master_project_types", "installation_id")
    op.create_unique_constraint(
        "uq_master_project_types_ets_id_language",
        "master_project_types",
        ["ets_id", "language_code"],
    )

    # --- location / function ---
    op.execute(sa.text("UPDATE locations SET ets_id = 'BP-MISSING-' || id::text WHERE ets_id IS NULL"))
    op.alter_column("locations", "ets_id", existing_type=sa.Text(), nullable=False)
    op.drop_column("locations", "puid")
    op.drop_column("location_versions", "type_description")
    op.execute(sa.text("UPDATE functions SET ets_id = 'F-MISSING-' || id::text WHERE ets_id IS NULL"))
    op.alter_column("functions", "ets_id", existing_type=sa.Text(), nullable=False)
    op.drop_column("functions", "puid")
    op.execute(
        sa.text("UPDATE function_versions SET function_type_ets_id = 'FT-0' WHERE function_type_ets_id IS NULL")
    )
    op.alter_column(
        "function_versions", "function_type_ets_id", existing_type=sa.Text(), nullable=False
    )
    op.drop_column("function_versions", "type_description")
    _add_completion("function_versions")

    # --- topology ---
    op.drop_column("areas", "puid")
    op.execute(sa.text("UPDATE area_versions SET address = 0 WHERE address IS NULL"))
    op.alter_column("area_versions", "address", existing_type=sa.Integer(), nullable=False)
    op.create_check_constraint("address", "area_versions", ADDRESS_SQL)
    op.add_column("area_versions", sa.Column("description", sa.Text(), nullable=True))
    _add_completion("area_versions")

    op.add_column("line_versions", sa.Column("area_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            "UPDATE line_versions lv SET area_id = l.area_id FROM lines l WHERE lv.line_id = l.id"
        )
    )
    op.alter_column("line_versions", "area_id", existing_type=UUID_TYPE, nullable=False)
    op.create_foreign_key(
        "fk_line_versions_area_id_areas",
        "line_versions",
        "areas",
        ["area_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_line_versions_area_id", "line_versions", ["area_id"])
    op.drop_index("ix_lines_area_id", table_name="lines")
    _drop_fk("lines", "area_id", "areas")
    op.drop_column("lines", "area_id")
    op.drop_column("lines", "puid")
    op.execute(sa.text("UPDATE line_versions SET address = 0 WHERE address IS NULL"))
    op.alter_column("line_versions", "address", existing_type=sa.Integer(), nullable=False)
    op.create_check_constraint("address", "line_versions", ADDRESS_SQL)
    op.add_column("line_versions", sa.Column("description", sa.Text(), nullable=True))
    _add_completion("line_versions")

    op.add_column("segment_versions", sa.Column("line_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            "UPDATE segment_versions sv SET line_id = s.line_id FROM segments s "
            "WHERE sv.segment_id = s.id"
        )
    )
    op.alter_column("segment_versions", "line_id", existing_type=UUID_TYPE, nullable=False)
    op.create_foreign_key(
        "fk_segment_versions_line_id_lines",
        "segment_versions",
        "lines",
        ["line_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_segment_versions_line_id", "segment_versions", ["line_id"])
    op.drop_index("ix_segments_line_id", table_name="segments")
    _drop_fk("segments", "line_id", "lines")
    op.drop_column("segments", "line_id")
    op.drop_column("segments", "puid")
    op.add_column("segment_versions", sa.Column("number", sa.Text(), nullable=True))
    op.add_column("segment_versions", sa.Column("description", sa.Text(), nullable=True))
    _add_completion("segment_versions")

    # --- group range / datapoint ---
    op.drop_column("group_ranges", "puid")
    op.add_column("group_range_versions", sa.Column("unfiltered", sa.Boolean(), nullable=True))
    op.add_column("group_range_versions", sa.Column("security", sa.Text(), nullable=True))
    _add_completion("group_range_versions")

    op.execute(sa.text("UPDATE datapoints SET ets_id = 'GA-MISSING-' || id::text WHERE ets_id IS NULL"))
    op.alter_column("datapoints", "ets_id", existing_type=sa.Text(), nullable=False)
    op.drop_column("datapoints", "puid")
    op.alter_column(
        "datapoint_versions",
        "title",
        new_column_name="name",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.drop_column("datapoint_versions", "datapoint_type")
    op.add_column("datapoint_versions", sa.Column("purpose", sa.Text(), nullable=True))
    op.add_column("datapoint_versions", sa.Column("unfiltered", sa.Boolean(), nullable=True))
    op.add_column("datapoint_versions", sa.Column("central", sa.Boolean(), nullable=True))
    op.add_column("datapoint_versions", sa.Column("global", sa.Boolean(), nullable=True))
    op.add_column("datapoint_versions", sa.Column("key", sa.Text(), nullable=True))
    _add_completion("datapoint_versions")

    # --- device ---
    op.execute(sa.text("UPDATE devices SET ets_id = 'DI-MISSING-' || id::text WHERE ets_id IS NULL"))
    op.alter_column("devices", "ets_id", existing_type=sa.Text(), nullable=False)
    op.drop_column("devices", "puid")
    op.drop_column("device_versions", "current_date_time")
    op.drop_column("device_versions", "type_description")
    op.add_column("device_versions", sa.Column("assigned_trade", sa.Text(), nullable=True))
    op.add_column(
        "device_versions",
        sa.Column("operates_for_trade", postgresql.ARRAY(sa.Text()), nullable=True),
    )

    op.add_column("comm_object_versions", sa.Column("channel_id", UUID_TYPE, nullable=True))
    op.add_column("comm_object_versions", sa.Column("folder_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE comm_object_versions v
            SET channel_id = c.channel_id, folder_id = c.folder_id
            FROM comm_objects c
            WHERE v.comm_object_id = c.id
            """
        )
    )
    op.create_foreign_key(
        "fk_comm_object_versions_channel_id_device_channels",
        "comm_object_versions",
        "device_channels",
        ["channel_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_comm_object_versions_folder_id_device_folders",
        "comm_object_versions",
        "device_folders",
        ["folder_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_comm_object_versions_channel_id", "comm_object_versions", ["channel_id"])
    op.create_index("ix_comm_object_versions_folder_id", "comm_object_versions", ["folder_id"])
    op.drop_index("ix_comm_objects_channel_id", table_name="comm_objects")
    _drop_fk("comm_objects", "channel_id", "device_channels")
    _drop_fk("comm_objects", "folder_id", "device_folders")
    op.drop_column("comm_objects", "channel_id")
    op.drop_column("comm_objects", "folder_id")

    op.execute(sa.text("UPDATE trades SET ets_id = 'T-MISSING-' || id::text WHERE ets_id IS NULL"))
    op.alter_column("trades", "ets_id", existing_type=sa.Text(), nullable=False)
    op.drop_column("trades", "puid")


def downgrade() -> None:
    op.add_column("trades", sa.Column("puid", sa.Integer(), nullable=True))
    op.alter_column("trades", "ets_id", existing_type=sa.Text(), nullable=True)

    op.add_column("comm_objects", sa.Column("channel_id", UUID_TYPE, nullable=True))
    op.add_column("comm_objects", sa.Column("folder_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE comm_objects c SET channel_id = v.channel_id, folder_id = v.folder_id
            FROM (
                SELECT DISTINCT ON (comm_object_id) comm_object_id, channel_id, folder_id
                FROM comm_object_versions
                ORDER BY comm_object_id, last_modified DESC
            ) v
            WHERE c.id = v.comm_object_id
            """
        )
    )
    op.create_foreign_key(
        "fk_comm_objects_channel_id_device_channels",
        "comm_objects",
        "device_channels",
        ["channel_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_comm_objects_folder_id_device_folders",
        "comm_objects",
        "device_folders",
        ["folder_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_comm_objects_channel_id", "comm_objects", ["channel_id"])
    op.drop_index("ix_comm_object_versions_folder_id", table_name="comm_object_versions")
    op.drop_index("ix_comm_object_versions_channel_id", table_name="comm_object_versions")
    op.drop_constraint(
        "fk_comm_object_versions_folder_id_device_folders",
        "comm_object_versions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_comm_object_versions_channel_id_device_channels",
        "comm_object_versions",
        type_="foreignkey",
    )
    op.drop_column("comm_object_versions", "folder_id")
    op.drop_column("comm_object_versions", "channel_id")

    op.drop_column("device_versions", "operates_for_trade")
    op.drop_column("device_versions", "assigned_trade")
    op.add_column("device_versions", sa.Column("type_description", sa.Text(), nullable=True))
    op.add_column(
        "device_versions", sa.Column("current_date_time", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("devices", sa.Column("puid", sa.Integer(), nullable=True))
    op.alter_column("devices", "ets_id", existing_type=sa.Text(), nullable=True)

    _drop_completion("datapoint_versions")
    op.drop_column("datapoint_versions", "key")
    op.drop_column("datapoint_versions", "global")
    op.drop_column("datapoint_versions", "central")
    op.drop_column("datapoint_versions", "unfiltered")
    op.drop_column("datapoint_versions", "purpose")
    op.add_column(
        "datapoint_versions",
        sa.Column("datapoint_type", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.execute(sa.text("UPDATE datapoint_versions SET name = COALESCE(name, '')"))
    op.alter_column(
        "datapoint_versions",
        "name",
        new_column_name="title",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.add_column("datapoints", sa.Column("puid", sa.Integer(), nullable=True))
    op.alter_column("datapoints", "ets_id", existing_type=sa.Text(), nullable=True)

    _drop_completion("group_range_versions")
    op.drop_column("group_range_versions", "security")
    op.drop_column("group_range_versions", "unfiltered")
    op.add_column("group_ranges", sa.Column("puid", sa.Integer(), nullable=True))

    _drop_completion("segment_versions")
    op.drop_column("segment_versions", "description")
    op.drop_column("segment_versions", "number")
    op.add_column("segments", sa.Column("line_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE segments s SET line_id = v.line_id
            FROM (
                SELECT DISTINCT ON (segment_id) segment_id, line_id
                FROM segment_versions ORDER BY segment_id, last_modified DESC
            ) v
            WHERE s.id = v.segment_id
            """
        )
    )
    op.alter_column("segments", "line_id", existing_type=UUID_TYPE, nullable=False)
    op.create_foreign_key(
        "fk_segments_line_id_lines",
        "segments",
        "lines",
        ["line_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_segments_line_id", "segments", ["line_id"])
    op.drop_index("ix_segment_versions_line_id", table_name="segment_versions")
    op.drop_constraint(
        op.f("fk_segment_versions_line_id_lines"), "segment_versions", type_="foreignkey"
    )
    op.drop_column("segment_versions", "line_id")
    op.add_column("segments", sa.Column("puid", sa.Integer(), nullable=True))

    _drop_completion("line_versions")
    op.drop_column("line_versions", "description")
    op.drop_constraint("address", "line_versions", type_="check")
    op.alter_column("line_versions", "address", existing_type=sa.Integer(), nullable=True)
    op.add_column("lines", sa.Column("area_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE lines l SET area_id = v.area_id
            FROM (
                SELECT DISTINCT ON (line_id) line_id, area_id
                FROM line_versions ORDER BY line_id, last_modified DESC
            ) v
            WHERE l.id = v.line_id
            """
        )
    )
    op.alter_column("lines", "area_id", existing_type=UUID_TYPE, nullable=False)
    op.create_foreign_key(
        "fk_lines_area_id_areas",
        "lines",
        "areas",
        ["area_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_lines_area_id", "lines", ["area_id"])
    op.drop_index("ix_line_versions_area_id", table_name="line_versions")
    op.drop_constraint(
        op.f("fk_line_versions_area_id_areas"), "line_versions", type_="foreignkey"
    )
    op.drop_column("line_versions", "area_id")
    op.add_column("lines", sa.Column("puid", sa.Integer(), nullable=True))

    _drop_completion("area_versions")
    op.drop_column("area_versions", "description")
    op.drop_constraint("address", "area_versions", type_="check")
    op.alter_column("area_versions", "address", existing_type=sa.Integer(), nullable=True)
    op.add_column("areas", sa.Column("puid", sa.Integer(), nullable=True))

    _drop_completion("function_versions")
    op.add_column("function_versions", sa.Column("type_description", sa.Text(), nullable=True))
    op.alter_column(
        "function_versions", "function_type_ets_id", existing_type=sa.Text(), nullable=True
    )
    op.add_column("functions", sa.Column("puid", sa.Integer(), nullable=True))
    op.alter_column("functions", "ets_id", existing_type=sa.Text(), nullable=True)
    op.add_column("location_versions", sa.Column("type_description", sa.Text(), nullable=True))
    op.add_column("locations", sa.Column("puid", sa.Integer(), nullable=True))
    op.alter_column("locations", "ets_id", existing_type=sa.Text(), nullable=True)

    op.drop_constraint(
        "uq_master_project_types_ets_id_language", "master_project_types", type_="unique"
    )
    op.add_column("master_project_types", sa.Column("installation_id", UUID_TYPE, nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE master_project_types SET installation_id = (
                SELECT id FROM installations LIMIT 1
            )
            """
        )
    )
    op.alter_column("master_project_types", "installation_id", existing_type=UUID_TYPE, nullable=True)
    op.create_foreign_key(
        "fk_master_project_types_installation_id_installations",
        "master_project_types",
        "installations",
        ["installation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_master_project_types_installation_id",
        "master_project_types",
        ["installation_id"],
    )
    op.create_unique_constraint(
        "uq_master_project_types_installation_ets_id_language",
        "master_project_types",
        ["installation_id", "ets_id", "language_code"],
    )

    op.drop_table("master_manufacturers")
    op.drop_table("master_function_points")

    op.add_column("master_medium_types", sa.Column("name", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_medium_types SET name = code"))
    op.drop_column("master_medium_types", "domain_address_length")
    op.drop_column("master_medium_types", "text")
    op.drop_column("master_medium_types", "code")
    op.drop_column("master_medium_types", "number")

    op.add_column("master_space_usages", sa.Column("name", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_space_usages SET name = text"))
    op.drop_column("master_space_usages", "text")
    op.drop_column("master_space_usages", "number")

    op.add_column("master_datapoint_roles", sa.Column("name", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_datapoint_roles SET name = code"))
    op.drop_column("master_datapoint_roles", "code")
    op.drop_column("master_datapoint_roles", "number")

    op.add_column("master_function_types", sa.Column("name", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_function_types SET name = text"))
    op.drop_column("master_function_types", "status")
    op.drop_column("master_function_types", "text")
    op.drop_column("master_function_types", "number")

    op.alter_column(
        "datafields",
        "datapoint_subtype_knx_id",
        new_column_name="datapoint_subtype_ets_id",
        existing_type=sa.Text(),
    )

    op.add_column("master_datapoint_subtypes", sa.Column("name", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_datapoint_subtypes SET name = text"))
    op.alter_column(
        "master_datapoint_subtypes",
        "datapoint_type_knx_id",
        new_column_name="datapoint_type_ets_id",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.drop_column("master_datapoint_subtypes", "is_default")
    op.drop_column("master_datapoint_subtypes", "number")
    op.drop_column("master_datapoint_subtypes", "code")
    op.drop_column("master_datapoint_subtypes", "text")

    op.add_column("master_datapoint_types", sa.Column("name", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE master_datapoint_types SET name = text"))
    op.alter_column(
        "master_datapoint_types", "size_in_bit", existing_type=sa.Integer(), nullable=True
    )
    op.drop_column("master_datapoint_types", "number")
    op.drop_column("master_datapoint_types", "code")
    op.drop_column("master_datapoint_types", "text")

    for table in CATALOGS:
        op.drop_index(f"ix_{table}_master_data_id", table_name=table)
        op.drop_constraint(f"uq_{table}_master_data_knx_id", table, type_="unique")
        op.drop_constraint(
            f"fk_{table}_master_data_id_master_data", table, type_="foreignkey"
        )
        op.alter_column(table, "knx_id", new_column_name="ets_id", existing_type=sa.Text())
        op.add_column(table, sa.Column("installation_id", UUID_TYPE, nullable=True))
        op.execute(
            sa.text(
                f"""
                UPDATE {table} SET installation_id = (SELECT id FROM installations LIMIT 1)
                """
            )
        )
        op.create_foreign_key(
            f"fk_{table}_installation_id_installations",
            table,
            "installations",
            ["installation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_unique_constraint(
            f"uq_{table}_installation_ets_id",
            table,
            ["installation_id", "ets_id"],
        )
        op.drop_column(table, "master_data_id")
    op.create_index("ix_datafields_installation_id", "datafields", ["installation_id"])

    op.drop_index("ix_master_translations_master_data_id", table_name="master_translations")
    op.drop_table("master_translations")
    op.drop_table("master_data")

    op.drop_constraint(
        op.f("pk_installation_subscriptions"), "installation_subscriptions", type_="primary"
    )
    op.drop_column("installation_subscriptions", "id")
    op.execute(
        sa.text(
            """
            ALTER TABLE installation_subscriptions
            ADD COLUMN id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
            """
        )
    )

    op.drop_column("installation_versions", "bcu_key")
    op.drop_column("installation_versions", "ip_routing_backbone_key")
    op.drop_column("installation_versions", "tool_version")
    op.drop_column("installation_versions", "created_by")
    op.drop_column("installation_versions", "schema_version")
    op.add_column("installation_versions", sa.Column("type_description", sa.Text(), nullable=True))

    op.add_column(
        "installations",
        sa.Column("group_address_style", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE installations i
            SET group_address_style = v.group_address_style
            FROM (
                SELECT DISTINCT ON (installation_id) installation_id, group_address_style
                FROM installation_versions
                ORDER BY installation_id, last_modified DESC
            ) v
            WHERE i.id = v.installation_id
            """
        )
    )
    op.create_check_constraint(
        op.f("ck_installations_group_address_style"),
        "installations",
        GROUP_ADDRESS_STYLE_SQL,
    )
    op.drop_constraint("group_address_style", "installation_versions", type_="check")
    op.drop_column("installation_versions", "group_address_style")

    op.add_column("installations", sa.Column("installation_index", sa.Integer(), nullable=True))
    op.add_column("installations", sa.Column("knx_project_id", sa.Text(), nullable=True))
    op.create_index("ix_installations_knx_project_id", "installations", ["knx_project_id"])
    op.alter_column("installations", "project_guid", existing_type=UUID_TYPE, nullable=True)
    op.alter_column("installations", "ets_id", existing_type=sa.Text(), nullable=True)
    op.drop_constraint("language_code", "installations", type_="check")
    op.drop_column("installations", "language_code")
    op.drop_column("installations", "project_start")
