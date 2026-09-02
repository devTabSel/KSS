"""Add datapoint_versions.at_type (3API meta.@type)

Revision ID: 008_datapoint_at_type
Revises: 007_drop_inst_language_code
Create Date: 2026-09-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_datapoint_at_type"
down_revision: Union[str, Sequence[str], None] = "007_drop_inst_language_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "datapoint_versions",
        sa.Column(
            "at_type",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            comment=(
                "3API item.meta.@type (z. B. knx:FunctionPoint, knx:dpa.417.61). "
                "Fill/Synthese mit Tag-Store, nicht Ingest-Pflicht."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("datapoint_versions", "at_type")
