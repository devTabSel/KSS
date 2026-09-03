"""Rename GA tables from datapoint* to group_address*

Revision ID: 010_group_addresses_rename
Revises: 009_device_serial_loaded
Create Date: 2026-09-03

Instance GroupAddress = ETS GA-n, sibling of group_ranges. KIM knx:FunctionPoint
is at_type only. 3API datapoint is CommObject. Catalog master_function_points
(FP-*) is unchanged.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_group_addresses_rename"
down_revision: Union[str, Sequence[str], None] = "009_device_serial_loaded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID_TYPE = postgresql.UUID(as_uuid=True)

OLD_ID_COMMENT = (
    "3API DatapointTypeAndId.id (uuid). Semantik hängt an dieser Id, "
    "nicht an der Busnummer."
)
NEW_ID_COMMENT = (
    "Stabile UUID. ETS GroupAddress (GA-n). "
    "Nicht 3API datapoint (das ist CommObject). "
    "KIM knx:FunctionPoint liegt auf Version.at_type."
)
OLD_NAME_COMMENT = None
NEW_NAME_COMMENT = (
    "ETS GroupAddress/@Name. Nicht 3API datapoint title (das ist CommObject)."
)
OLD_AT_TYPE_COMMENT = (
    "3API item.meta.@type (z. B. knx:FunctionPoint, knx:dpa.417.61). "
    "Fill/Synthese mit Tag-Store, nicht Ingest-Pflicht."
)
NEW_AT_TYPE_COMMENT = (
    "KIM/JSON-LD @type (z. B. knx:FunctionPoint, knx:dpa.417.61). "
    "FunctionPoint ist @type, nicht die Tabelle. "
    "Fill/Synthese mit Tag-Store, nicht Ingest-Pflicht."
)
OLD_GA_INT_COMMENT = (
    "16-Bit GroupAddress/@Address / knx:groupAddress. "
    "Anzeige aus Stil + diesem Integer, keine Haupt-/Mittelgruppe-Spalten."
)
NEW_GA_INT_COMMENT = (
    "16-Bit GroupAddress/@Address / knx:groupAddress (Busnummer). "
    "Nicht die Entitäts-UUID. Anzeige aus Stil + diesem Integer."
)


def _rename_constraint(table: str, old: str, new: str) -> None:
    op.execute(sa.text(f'ALTER TABLE {table} RENAME CONSTRAINT "{old}" TO "{new}"'))


def _rename_index(old: str, new: str) -> None:
    op.execute(sa.text(f'ALTER INDEX "{old}" RENAME TO "{new}"'))


def upgrade() -> None:
    op.rename_table("datapoints", "group_addresses")
    op.rename_table("datapoint_versions", "group_address_versions")
    op.rename_table("function_datapoints", "function_group_addresses")
    op.rename_table("comm_object_datapoints", "comm_object_group_addresses")

    op.alter_column(
        "group_address_versions",
        "datapoint_id",
        new_column_name="group_address_id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
    )
    op.alter_column(
        "function_group_addresses",
        "datapoint_id",
        new_column_name="group_address_id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
    )
    op.alter_column(
        "comm_object_group_addresses",
        "datapoint_id",
        new_column_name="group_address_id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
    )

    _rename_constraint("group_addresses", "pk_datapoints", "pk_group_addresses")
    _rename_constraint(
        "group_addresses",
        "uq_datapoints_installation_ets_id",
        "uq_group_addresses_installation_ets_id",
    )
    _rename_constraint(
        "group_addresses",
        "fk_datapoints_installation_id_installations",
        "fk_group_addresses_installation_id_installations",
    )
    _rename_index("ix_datapoints_installation_id", "ix_group_addresses_installation_id")

    _rename_constraint(
        "group_address_versions",
        "pk_datapoint_versions",
        "pk_group_address_versions",
    )
    _rename_constraint(
        "group_address_versions",
        "ck_datapoint_versions_group_address",
        "ck_group_address_versions_group_address",
    )
    _rename_constraint(
        "group_address_versions",
        "ck_datapoint_versions_completion_status",
        "ck_group_address_versions_completion_status",
    )
    _rename_constraint(
        "group_address_versions",
        "fk_datapoint_versions_datapoint_id_datapoints",
        "fk_group_address_versions_group_address_id_group_addresses",
    )
    _rename_constraint(
        "group_address_versions",
        "fk_datapoint_versions_group_range_id_group_ranges",
        "fk_group_address_versions_group_range_id_group_ranges",
    )
    _rename_index(
        "ix_datapoint_versions_group_address",
        "ix_group_address_versions_group_address",
    )
    _rename_index(
        "ix_datapoint_versions_group_range_id",
        "ix_group_address_versions_group_range_id",
    )

    _rename_constraint(
        "function_group_addresses",
        "pk_function_datapoints",
        "pk_function_group_addresses",
    )
    _rename_constraint(
        "function_group_addresses",
        "fk_function_datapoints_function_id_functions",
        "fk_function_group_addresses_function_id_functions",
    )
    _rename_constraint(
        "function_group_addresses",
        "fk_function_datapoints_datapoint_id_datapoints",
        "fk_function_group_addresses_group_address_id_group_addresses",
    )
    _rename_index(
        "ix_function_datapoints_datapoint_id",
        "ix_function_group_addresses_group_address_id",
    )

    _rename_constraint(
        "comm_object_group_addresses",
        "pk_comm_object_datapoints",
        "pk_comm_object_group_addresses",
    )
    _rename_constraint(
        "comm_object_group_addresses",
        "fk_comm_object_datapoints_comm_object_id_comm_objects",
        "fk_comm_object_group_addresses_comm_object_id_comm_objects",
    )
    _rename_constraint(
        "comm_object_group_addresses",
        "fk_comm_object_datapoints_datapoint_id_datapoints",
        "fk_comm_object_group_addresses_group_address_id_group_addresses",
    )
    _rename_index(
        "ix_comm_object_datapoints_datapoint_id",
        "ix_comm_object_group_addresses_group_address_id",
    )

    op.alter_column(
        "group_addresses",
        "id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
        comment=NEW_ID_COMMENT,
        existing_comment=OLD_ID_COMMENT,
    )
    op.alter_column(
        "group_address_versions",
        "name",
        existing_type=sa.Text(),
        existing_nullable=True,
        comment=NEW_NAME_COMMENT,
        existing_comment=OLD_NAME_COMMENT,
    )
    op.alter_column(
        "group_address_versions",
        "at_type",
        existing_type=postgresql.ARRAY(sa.Text()),
        existing_nullable=True,
        comment=NEW_AT_TYPE_COMMENT,
        existing_comment=OLD_AT_TYPE_COMMENT,
    )
    op.alter_column(
        "group_address_versions",
        "group_address",
        existing_type=sa.Integer(),
        existing_nullable=True,
        comment=NEW_GA_INT_COMMENT,
        existing_comment=OLD_GA_INT_COMMENT,
    )


def downgrade() -> None:
    op.alter_column(
        "group_address_versions",
        "group_address",
        existing_type=sa.Integer(),
        existing_nullable=True,
        comment=OLD_GA_INT_COMMENT,
        existing_comment=NEW_GA_INT_COMMENT,
    )
    op.alter_column(
        "group_address_versions",
        "at_type",
        existing_type=postgresql.ARRAY(sa.Text()),
        existing_nullable=True,
        comment=OLD_AT_TYPE_COMMENT,
        existing_comment=NEW_AT_TYPE_COMMENT,
    )
    op.alter_column(
        "group_address_versions",
        "name",
        existing_type=sa.Text(),
        existing_nullable=True,
        comment=OLD_NAME_COMMENT,
        existing_comment=NEW_NAME_COMMENT,
    )
    op.alter_column(
        "group_addresses",
        "id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
        comment=OLD_ID_COMMENT,
        existing_comment=NEW_ID_COMMENT,
    )

    _rename_index(
        "ix_comm_object_group_addresses_group_address_id",
        "ix_comm_object_datapoints_datapoint_id",
    )
    _rename_constraint(
        "comm_object_group_addresses",
        "fk_comm_object_group_addresses_group_address_id_group_addresses",
        "fk_comm_object_datapoints_datapoint_id_datapoints",
    )
    _rename_constraint(
        "comm_object_group_addresses",
        "fk_comm_object_group_addresses_comm_object_id_comm_objects",
        "fk_comm_object_datapoints_comm_object_id_comm_objects",
    )
    _rename_constraint(
        "comm_object_group_addresses",
        "pk_comm_object_group_addresses",
        "pk_comm_object_datapoints",
    )

    _rename_index(
        "ix_function_group_addresses_group_address_id",
        "ix_function_datapoints_datapoint_id",
    )
    _rename_constraint(
        "function_group_addresses",
        "fk_function_group_addresses_group_address_id_group_addresses",
        "fk_function_datapoints_datapoint_id_datapoints",
    )
    _rename_constraint(
        "function_group_addresses",
        "fk_function_group_addresses_function_id_functions",
        "fk_function_datapoints_function_id_functions",
    )
    _rename_constraint(
        "function_group_addresses",
        "pk_function_group_addresses",
        "pk_function_datapoints",
    )

    _rename_index(
        "ix_group_address_versions_group_range_id",
        "ix_datapoint_versions_group_range_id",
    )
    _rename_index(
        "ix_group_address_versions_group_address",
        "ix_datapoint_versions_group_address",
    )
    _rename_constraint(
        "group_address_versions",
        "fk_group_address_versions_group_range_id_group_ranges",
        "fk_datapoint_versions_group_range_id_group_ranges",
    )
    _rename_constraint(
        "group_address_versions",
        "fk_group_address_versions_group_address_id_group_addresses",
        "fk_datapoint_versions_datapoint_id_datapoints",
    )
    _rename_constraint(
        "group_address_versions",
        "ck_group_address_versions_completion_status",
        "ck_datapoint_versions_completion_status",
    )
    _rename_constraint(
        "group_address_versions",
        "ck_group_address_versions_group_address",
        "ck_datapoint_versions_group_address",
    )
    _rename_constraint(
        "group_address_versions",
        "pk_group_address_versions",
        "pk_datapoint_versions",
    )

    _rename_index("ix_group_addresses_installation_id", "ix_datapoints_installation_id")
    _rename_constraint(
        "group_addresses",
        "fk_group_addresses_installation_id_installations",
        "fk_datapoints_installation_id_installations",
    )
    _rename_constraint(
        "group_addresses",
        "uq_group_addresses_installation_ets_id",
        "uq_datapoints_installation_ets_id",
    )
    _rename_constraint("group_addresses", "pk_group_addresses", "pk_datapoints")

    op.alter_column(
        "comm_object_group_addresses",
        "group_address_id",
        new_column_name="datapoint_id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
    )
    op.alter_column(
        "function_group_addresses",
        "group_address_id",
        new_column_name="datapoint_id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
    )
    op.alter_column(
        "group_address_versions",
        "group_address_id",
        new_column_name="datapoint_id",
        existing_type=UUID_TYPE,
        existing_nullable=False,
    )

    op.rename_table("comm_object_group_addresses", "comm_object_datapoints")
    op.rename_table("function_group_addresses", "function_datapoints")
    op.rename_table("group_address_versions", "datapoint_versions")
    op.rename_table("group_addresses", "datapoints")
