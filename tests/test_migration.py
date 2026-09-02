from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from kss.db import engine

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "kss_alembic_unified_test"

EXPECTED_TABLES = {
    "installations",
    "installation_versions",
    "installation_subscriptions",
    "master_data",
    "master_translations",
    "master_function_points",
    "master_manufacturers",
    "master_datapoint_types",
    "master_datapoint_subtypes",
    "datafields",
    "master_function_types",
    "master_datapoint_roles",
    "master_space_usages",
    "master_medium_types",
    "master_project_types",
    "areas",
    "area_versions",
    "lines",
    "line_versions",
    "segments",
    "segment_versions",
    "locations",
    "location_versions",
    "functions",
    "function_versions",
    "function_datapoints",
    "group_ranges",
    "group_range_versions",
    "datapoints",
    "datapoint_versions",
    "devices",
    "device_versions",
    "device_channels",
    "device_channel_versions",
    "device_folders",
    "device_folder_versions",
    "comm_objects",
    "comm_object_versions",
    "comm_object_datapoints",
    "trades",
    "trade_versions",
    "trade_devices",
    "bus_pa_bindings",
    "bus_ga_bindings",
}


def _alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_alembic_upgrade_and_downgrade_on_empty_schema() -> None:
    url = (
        "postgresql+psycopg://kss:kss@localhost:5432/kss"
        f"?options=-csearch_path%%3D{SCHEMA}"
    )
    with engine.connect() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        connection.execute(text(f"CREATE SCHEMA {SCHEMA}"))
        connection.commit()

    try:
        config = _alembic_config(url)
        command.upgrade(config, "head")

        with engine.connect() as connection:
            connection.execute(text(f"SET search_path TO {SCHEMA}, public"))
            tables = set(
                connection.execute(
                    text(
                        """
                        SELECT tablename
                        FROM pg_tables
                        WHERE schemaname = :schema
                        ORDER BY tablename
                        """
                    ),
                    {"schema": SCHEMA},
                ).scalars().all()
            )
            fk_count = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.table_constraints
                    WHERE table_schema = :schema
                      AND constraint_type = 'FOREIGN KEY'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            primary_keys = connection.execute(
                text(
                    """
                    SELECT tc.table_name,
                           string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position)
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_schema = kcu.table_schema
                    WHERE tc.table_schema = :schema
                      AND tc.constraint_type = 'PRIMARY KEY'
                    GROUP BY tc.table_name
                    """
                ),
                {"schema": SCHEMA},
            ).all()
            exclude = connection.execute(
                text(
                    """
                    SELECT conname
                    FROM pg_constraint c
                    JOIN pg_namespace n ON n.oid = c.connamespace
                    WHERE n.nspname = :schema AND c.contype = 'x'
                    """
                ),
                {"schema": SCHEMA},
            ).scalars().all()
            device_location_fk = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.referential_constraints rc
                    JOIN information_schema.key_column_usage kcu
                      ON rc.constraint_name = kcu.constraint_name
                     AND rc.constraint_schema = kcu.constraint_schema
                    WHERE rc.constraint_schema = :schema
                      AND kcu.table_name = 'device_versions'
                      AND kcu.column_name = 'location_id'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            trade_device_fk = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.key_column_usage
                    WHERE table_schema = :schema
                      AND table_name = 'trade_devices'
                      AND column_name = 'device_id'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            project_type_column = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = 'installation_versions'
                      AND column_name = 'project_type'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            catalog_unique = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.table_constraints
                    WHERE table_schema = :schema
                      AND table_name = 'master_project_types'
                      AND constraint_type = 'UNIQUE'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            folder_parent_channel = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = 'device_folder_versions'
                      AND column_name = 'parent_channel_id'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            channel_parent = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = 'device_channel_versions'
                      AND column_name = 'parent_channel_id'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            folder_xor = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM pg_constraint c
                    JOIN pg_namespace n ON n.oid = c.connamespace
                    WHERE n.nspname = :schema
                      AND c.contype = 'c'
                      AND c.conname = 'ck_device_folder_versions_parent_xor'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            nested_channel_not_self = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM pg_constraint c
                    JOIN pg_namespace n ON n.oid = c.connamespace
                    WHERE n.nspname = :schema
                      AND c.contype = 'c'
                      AND c.conname = 'ck_device_channel_versions_parent_not_self'
                    """
                ),
                {"schema": SCHEMA},
            ).scalar_one()
            channel_version_columns = set(
                connection.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = :schema
                          AND table_name = 'device_channel_versions'
                        """
                    ),
                    {"schema": SCHEMA},
                ).scalars().all()
            )

        pk_by_table = {row[0]: row[1] for row in primary_keys}
        assert EXPECTED_TABLES <= tables
        assert fk_count >= 30
        assert pk_by_table["installation_versions"] == "installation_id,last_modified"
        assert pk_by_table["trade_devices"] == "trade_id,device_id,last_modified"
        assert pk_by_table["function_datapoints"] == "function_id,datapoint_id,last_modified"
        assert pk_by_table["comm_object_datapoints"] == "comm_object_id,datapoint_id,last_modified"
        assert pk_by_table["bus_pa_bindings"] == "installation_id,individual_address,last_downloaded"
        assert pk_by_table["bus_ga_bindings"] == "installation_id,group_address,device_id,last_downloaded"
        assert exclude == []
        assert device_location_fk >= 1
        assert trade_device_fk >= 1
        assert project_type_column == 1
        assert catalog_unique >= 1
        assert folder_parent_channel == 1
        assert channel_parent == 1
        assert folder_xor == 1
        assert nested_channel_not_self == 1
        assert "description" in channel_version_columns
        assert "is_active" not in channel_version_columns
        assert "parent_folder_id" not in channel_version_columns

        command.downgrade(config, "base")
        with engine.connect() as connection:
            remaining = connection.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = :schema
                      AND tablename <> 'alembic_version'
                    """
                ),
                {"schema": SCHEMA},
            ).scalars().all()
        assert remaining == []

        command.upgrade(config, "head")
    finally:
        with engine.connect() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
            connection.commit()
