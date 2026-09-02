"""Drop language_code from installations (parser overlay, not identity)

Revision ID: 007_drop_inst_language_code
Revises: 006_modellierung_feldlisten
Create Date: 2026-09-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from kss.models.constants import LANGUAGE_CODE_SQL

revision: str = "007_drop_inst_language_code"
down_revision: Union[str, Sequence[str], None] = "006_modellierung_feldlisten"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("language_code", "installations", type_="check")
    op.drop_column("installations", "language_code")


def downgrade() -> None:
    op.add_column("installations", sa.Column("language_code", sa.Text(), nullable=True))
    op.create_check_constraint(
        "language_code",
        "installations",
        f"language_code IS NULL OR {LANGUAGE_CODE_SQL}",
    )
