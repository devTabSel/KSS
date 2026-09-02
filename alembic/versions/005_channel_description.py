"""ChannelInstance Description on device_channel_versions

Revision ID: 005_channel_description
Revises: 004_got_parent_edges
Create Date: 2026-09-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_channel_description"
down_revision: Union[str, Sequence[str], None] = "004_got_parent_edges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DESCRIPTION_COMMENT = "Kategorie 3. ChannelInstance/@Description. GOT-only NULL."


def upgrade() -> None:
    op.add_column(
        "device_channel_versions",
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment=DESCRIPTION_COMMENT,
        ),
    )


def downgrade() -> None:
    op.drop_column("device_channel_versions", "description")
