"""unified persistence model (all packets)

Revision ID: 001_unified
Revises:
Create Date: 2026-09-01

Tabellen, Constraints und Indizes kommen aus den SQLAlchemy-Modellen
(eine Quelle). create_all auf leerer Datenbank erzeugt das vollständige Schema.
"""

from typing import Sequence, Union

from alembic import op

from kss.models.base import Base
import kss.models  # noqa: F401

revision: str = "001_unified"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
