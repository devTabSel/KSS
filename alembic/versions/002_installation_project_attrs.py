"""installation project_type and language-aware catalog

Revision ID: 002_installation_project_attrs
Revises: 001_unified
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from kss.models.constants import (
    LANGUAGE_CODE_SQL,
    MASTER_PROJECT_TYPE_ETS_ID_SQL,
    PROJECT_TYPE_SQL,
)

revision: str = "002_installation_project_attrs"
down_revision: Union[str, Sequence[str], None] = "001_unified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "installation_versions",
        sa.Column(
            "project_type",
            sa.Text(),
            nullable=True,
            comment=(
                "Kategorie 3. knxproj ProjectInformation/@ProjectType. "
                "XSD 23 ProjectType_t (XML-Token, z. B. Family House). "
                "Nicht in der 3API, nicht in KIM. Anzeigenamen sprachabhängig "
                "in master_project_types. XML-Omit = XSD-Default "
                "Other (Commercial); leere optionale Felder bleiben nullable."
            ),
        ),
    )
    op.create_check_constraint(
        op.f("ck_installation_versions_project_type"),
        "installation_versions",
        PROJECT_TYPE_SQL,
    )
    op.create_table(
        "master_project_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "ets_id",
            sa.Text(),
            nullable=False,
            comment=(
                "Kategorie 3. XSD 23 ProjectType_t / "
                "ProjectInformation/@ProjectType, z. B. Family House."
            ),
        ),
        sa.Column(
            "language_code",
            sa.Text(),
            nullable=False,
            comment=(
                "Kategorie 3. Sprachcode analog knx_master Language/@Identifier "
                "(de-DE, en-US) oder kürzer (en)."
            ),
        ),
        sa.Column(
            "name",
            sa.Text(),
            nullable=False,
            comment=(
                "Kategorie 3. Sprachabhängiger Anzeigename, z. B. Familienhaus "
                "für ets_id Family House und language_code de-DE."
            ),
        ),
        sa.CheckConstraint(
            MASTER_PROJECT_TYPE_ETS_ID_SQL,
            name=op.f("ck_master_project_types_ets_id"),
        ),
        sa.CheckConstraint(
            LANGUAGE_CODE_SQL,
            name=op.f("ck_master_project_types_language_code"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0",
            name=op.f("ck_master_project_types_name"),
        ),
        sa.ForeignKeyConstraint(
            ["installation_id"],
            ["installations.id"],
            name=op.f("fk_master_project_types_installation_id_installations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_master_project_types")),
        sa.UniqueConstraint(
            "installation_id",
            "ets_id",
            "language_code",
            name="uq_master_project_types_installation_ets_id_language",
        ),
    )
    op.create_index(
        "ix_master_project_types_installation_id",
        "master_project_types",
        ["installation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_master_project_types_installation_id",
        table_name="master_project_types",
    )
    op.drop_table("master_project_types")
    op.drop_constraint(
        op.f("ck_installation_versions_project_type"),
        "installation_versions",
        type_="check",
    )
    op.drop_column("installation_versions", "project_type")
