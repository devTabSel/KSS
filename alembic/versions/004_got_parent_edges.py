"""GroupObjectTree parent edges: folder XOR, nested channel

Revision ID: 004_got_parent_edges
Revises: 003_temporal_lm_bus
Create Date: 2026-09-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_got_parent_edges"
down_revision: Union[str, Sequence[str], None] = "003_temporal_lm_bus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ETS_ID_COMMENT = (
    "Kategorie 3. Unique (device_id, ets_id). "
    "Mit ChannelInstance: @Id ohne XML-Präfix P-<ProjectId>-<Index>_ "
    "(DI-n_CI-n oder DI-n_M-…_CI-1); TTL-Join prj:<ets_id>. "
    "Ohne ChannelInstance: GroupObjectTree Node[@Type=Channel]/@RefId "
    "(CH-Basic, CH-UCT, MD-…_CH-4) — nicht TTL CI-n "
    "(Baumordnung ≠ CI-Index). "
    "ChannelInstance und Tree-Node mit gleichem @RefId = eine Zeile. "
    "Leere Kanäle (keine COs) bleiben zulässig."
)

CATALOG_REF_COMMENT = (
    "Kategorie 3. Katalog-RefId: ChannelInstance/@RefId bzw. "
    "GroupObjectTree Node[@Type=Channel]/@RefId "
    "(CH-3, CH-Basic, MD-…_CH-4). Join ChannelInstance ↔ Tree-Node."
)

OLD_ETS_ID_COMMENT = (
    "Kategorie 3. ChannelInstance-Fragment, z. B. CI-9 oder DI-65_CI-9."
)
OLD_CATALOG_REF_COMMENT = (
    "Kategorie 3. ChannelInstance/@RefId, z. B. CH-3 oder MD-…_CH-4."
)


def upgrade() -> None:
    op.add_column(
        "device_folder_versions",
        sa.Column(
            "parent_channel_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "Kategorie 3. GroupObjectTree: Folder-Node direkt unter "
                "Channel-Node. XOR mit parent_folder_id; beide NULL = Parent Device."
            ),
        ),
    )
    op.create_foreign_key(
        op.f("fk_device_folder_versions_parent_channel_id_device_channels"),
        "device_folder_versions",
        "device_channels",
        ["parent_channel_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_device_folder_versions_parent_xor"),
        "device_folder_versions",
        "parent_folder_id IS NULL OR parent_channel_id IS NULL",
    )
    op.create_index(
        "ix_device_folder_versions_parent_channel_id",
        "device_folder_versions",
        ["parent_channel_id"],
        unique=False,
    )
    op.create_index(
        "ix_device_folder_versions_parent_folder_id",
        "device_folder_versions",
        ["parent_folder_id"],
        unique=False,
    )
    op.alter_column(
        "device_folder_versions",
        "parent_folder_id",
        existing_type=postgresql.UUID(as_uuid=True),
        comment=(
            "Kategorie 3. Parent Folder-Node. XOR mit parent_channel_id; "
            "beide NULL = Parent Device (device_folders.device_id ist Besitz, "
            "nicht Tree-Parent)."
        ),
        existing_nullable=True,
    )

    op.add_column(
        "device_channel_versions",
        sa.Column(
            "parent_channel_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "Kategorie 3. GroupObjectTree: Channel-Node unter Channel-Node "
                "(WA53H10 DI-88 CH-1 → CH-ENO1). NULL = Parent Device."
            ),
        ),
    )
    op.create_foreign_key(
        op.f("fk_device_channel_versions_parent_channel_id_device_channels"),
        "device_channel_versions",
        "device_channels",
        ["parent_channel_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_device_channel_versions_parent_not_self"),
        "device_channel_versions",
        "parent_channel_id IS DISTINCT FROM channel_id",
    )
    op.create_index(
        "ix_device_channel_versions_parent_channel_id",
        "device_channel_versions",
        ["parent_channel_id"],
        unique=False,
    )

    op.alter_column(
        "device_channels",
        "ets_id",
        existing_type=sa.Text(),
        comment=ETS_ID_COMMENT,
        existing_nullable=False,
    )
    op.alter_column(
        "device_channel_versions",
        "catalog_ref",
        existing_type=sa.Text(),
        comment=CATALOG_REF_COMMENT,
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "device_channel_versions",
        "catalog_ref",
        existing_type=sa.Text(),
        comment=OLD_CATALOG_REF_COMMENT,
        existing_nullable=True,
    )
    op.alter_column(
        "device_channels",
        "ets_id",
        existing_type=sa.Text(),
        comment=OLD_ETS_ID_COMMENT,
        existing_nullable=False,
    )

    op.drop_index(
        "ix_device_channel_versions_parent_channel_id",
        table_name="device_channel_versions",
    )
    op.drop_constraint(
        op.f("ck_device_channel_versions_parent_not_self"),
        "device_channel_versions",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_device_channel_versions_parent_channel_id_device_channels"),
        "device_channel_versions",
        type_="foreignkey",
    )
    op.drop_column("device_channel_versions", "parent_channel_id")

    op.alter_column(
        "device_folder_versions",
        "parent_folder_id",
        existing_type=postgresql.UUID(as_uuid=True),
        comment=None,
        existing_nullable=True,
    )
    op.drop_index(
        "ix_device_folder_versions_parent_folder_id",
        table_name="device_folder_versions",
    )
    op.drop_index(
        "ix_device_folder_versions_parent_channel_id",
        table_name="device_folder_versions",
    )
    op.drop_constraint(
        op.f("ck_device_folder_versions_parent_xor"),
        "device_folder_versions",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_device_folder_versions_parent_channel_id_device_channels"),
        "device_folder_versions",
        type_="foreignkey",
    )
    op.drop_column("device_folder_versions", "parent_channel_id")
