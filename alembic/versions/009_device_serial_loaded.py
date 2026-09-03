"""Align device_versions serial_number comment and *Loaded NOT NULL defaults

Revision ID: 009_device_serial_loaded
Revises: 008_datapoint_at_type
Create Date: 2026-09-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_device_serial_loaded"
down_revision: Union[str, Sequence[str], None] = "008_datapoint_at_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LOADED_COLUMNS = (
    (
        "communication_part_loaded",
        "Kategorie 3. CommunicationPartLoaded. Allein kein Nachweis für "
        "LastDownload (Dummy-IP-Geräte).",
    ),
    ("individual_address_loaded", "Kategorie 3. IndividualAddressLoaded."),
    ("application_program_loaded", "Kategorie 3. ApplicationProgramLoaded."),
    ("parameters_loaded", "Kategorie 3. ParametersLoaded."),
    ("medium_config_loaded", "Kategorie 3. MediumConfigLoaded."),
)

SERIAL_NUMBER_COMMENT = (
    "3API serialNumber; roh Base64 wie knxproj/xknxproject (@SerialNumber); "
    'Omit/"" → NULL. Not hex. TTL $hex is converted to the same Base64 by '
    "the importer (Representer), not in the model."
)

OLD_SERIAL_NUMBER_COMMENT = (
    "3API serialNumber. Eine Spalte: 12 Hex-Zeichen der 6 Bytes "
    "(TTL $hex, XML Base64 → Importer wandelt)."
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE device_versions
            SET
                communication_part_loaded = COALESCE(communication_part_loaded, false),
                individual_address_loaded = COALESCE(individual_address_loaded, false),
                application_program_loaded = COALESCE(application_program_loaded, false),
                parameters_loaded = COALESCE(parameters_loaded, false),
                medium_config_loaded = COALESCE(medium_config_loaded, false)
            """
        )
    )
    for name, comment in LOADED_COLUMNS:
        op.alter_column(
            "device_versions",
            name,
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            existing_nullable=True,
            existing_comment=comment,
        )
    op.alter_column(
        "device_versions",
        "serial_number",
        existing_type=sa.Text(),
        comment=SERIAL_NUMBER_COMMENT,
        existing_nullable=True,
        existing_comment=OLD_SERIAL_NUMBER_COMMENT,
    )


def downgrade() -> None:
    op.alter_column(
        "device_versions",
        "serial_number",
        existing_type=sa.Text(),
        comment=OLD_SERIAL_NUMBER_COMMENT,
        existing_nullable=True,
        existing_comment=SERIAL_NUMBER_COMMENT,
    )
    for name, comment in LOADED_COLUMNS:
        op.alter_column(
            "device_versions",
            name,
            existing_type=sa.Boolean(),
            nullable=True,
            server_default=None,
            existing_nullable=False,
            existing_server_default=sa.false(),
            existing_comment=comment,
        )
