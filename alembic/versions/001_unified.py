"""unified persistence model (all packets)

Revision ID: 001_unified
Revises:
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_unified"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('installations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API InstallationTypeAndId.id (uuid).'),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj Project/@Id + InstallationIndex, z. B. P-040E-0. TTL prj:P-040E-0.'),
    sa.Column('project_guid', postgresql.UUID(as_uuid=True), nullable=True, comment='Kategorie 3. ProjectInformation/@Guid = TTL-Namespace http://iot.knx.org/{Guid}#.'),
    sa.Column('knx_project_id', sa.Text(), nullable=True, comment='Kategorie 3. Project/@Id ohne InstallationIndex, z. B. P-040E.'),
    sa.Column('installation_index', sa.Integer(), nullable=True, comment='Kategorie 3. Installation-Index im knxproj (meist 0).'),
    sa.Column('group_address_style', sa.Text(), nullable=True, comment='Kategorie 3. ProjectInformation/@GroupAddressStyle. ThreeLevel | TwoLevel | Free. Nicht historisiert.'),
    sa.CheckConstraint("group_address_style IS NULL OR group_address_style IN ('ThreeLevel', 'TwoLevel', 'Free')", name=op.f('ck_installations_group_address_style')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_installations')),
    sa.UniqueConstraint('ets_id', name='uq_installations_ets_id'),
    sa.UniqueConstraint('project_guid', name='uq_installations_project_guid')
    )
    op.create_index('ix_installations_knx_project_id', 'installations', ['knx_project_id'], unique=False)
    op.create_table('areas',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. knxproj-Suffix, z. B. A-1. Nicht im TTL.'),
    sa.Column('puid', sa.Integer(), nullable=True, comment='Kategorie 3. knxproj @Puid, XML-only, nie wiederverwendet.'),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_areas_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_areas')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_areas_installation_ets_id')
    )
    op.create_index('ix_areas_installation_id', 'areas', ['installation_id'], unique=False)
    op.create_table('datafields',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API DatafieldTypeAndId.id (uuid).'),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. Format-Id, z. B. DPST-1-2_F-1.'),
    sa.Column('title', sa.Text(), nullable=False, comment='3API attributes.title.'),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('datapoint_subtype_ets_id', sa.Text(), nullable=True, comment='DPST-*, dem dieses Format-Feld zugeordnet ist.'),
    sa.Column('kind', sa.Text(), nullable=True, comment='3API oneOf: enum | numbered | datetime | string.'),
    sa.Column('enum_value_map', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='3API attributes.enumValueMap.'),
    sa.Column('unit', sa.Text(), nullable=True),
    sa.Column('minimum', sa.Numeric(), nullable=True),
    sa.Column('maximum', sa.Numeric(), nullable=True),
    sa.Column('resolution', sa.Numeric(), nullable=True),
    sa.Column('integer', sa.Boolean(), nullable=True),
    sa.Column('charset', sa.Text(), nullable=True),
    sa.Column('max_length', sa.Integer(), nullable=True),
    sa.CheckConstraint("kind IS NULL OR kind IN ('enum', 'numbered', 'datetime', 'string')", name=op.f('ck_datafields_kind')),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_datafields_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_datafields')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_datafields_installation_ets_id')
    )
    op.create_index('ix_datafields_installation_id', 'datafields', ['installation_id'], unique=False)
    op.create_table('datapoints',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API DatapointTypeAndId.id (uuid). Semantik hängt an dieser Id, nicht an der Busnummer.'),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj-Suffix GA-n. TTL prj:GA-n.'),
    sa.Column('puid', sa.Integer(), nullable=True, comment='Kategorie 3. knxproj @Puid, XML-only.'),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_datapoints_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_datapoints')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_datapoints_installation_ets_id')
    )
    op.create_index('ix_datapoints_installation_id', 'datapoints', ['installation_id'], unique=False)
    op.create_table('devices',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API DeviceTypeAndId.id (uuid).'),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj-Suffix DI-n. TTL prj:DI-n.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_devices_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_devices')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_devices_installation_ets_id')
    )
    op.create_index('ix_devices_installation_id', 'devices', ['installation_id'], unique=False)
    op.create_table('functions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API FunctionTypeAndId.id (uuid).'),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj-Suffix F-n. TTL prj:F-n.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_functions_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_functions')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_functions_installation_ets_id')
    )
    op.create_index('ix_functions_installation_id', 'functions', ['installation_id'], unique=False)
    op.create_table('group_ranges',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. knxproj-Suffix GR-n. Nicht im TTL.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_group_ranges_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_group_ranges')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_group_ranges_installation_ets_id')
    )
    op.create_index('ix_group_ranges_installation_id', 'group_ranges', ['installation_id'], unique=False)
    op.create_table('installation_subscriptions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API installation id.'),
    sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API subscription id (Subscription-Entität nicht in diesem Modell).'),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_installation_subscriptions_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_installation_subscriptions')),
    sa.UniqueConstraint('installation_id', 'subscription_id', name='uq_installation_subscriptions_pair')
    )
    op.create_index('ix_installation_subscriptions_installation_id', 'installation_subscriptions', ['installation_id'], unique=False)
    op.create_index('ix_installation_subscriptions_subscription_id', 'installation_subscriptions', ['subscription_id'], unique=False)
    op.create_table('installation_versions',
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False, comment='FK zur stabilen Installations-Identität.'),
    sa.Column('title', sa.Text(), nullable=False, comment='3API attributes.title. Quelle knxproj: ProjectInformation/@Name (Installation/@Name oft leer). TTL dct:title.'),
    sa.Column('comment', sa.Text(), nullable=True, comment='3API attributes.comment (nullable). RTF möglich.'),
    sa.Column('contract_number', sa.Text(), nullable=True, comment='3API attributes.contractNumber (nullable).'),
    sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True, comment='3API attributes.lastModified / ProjectInformation/@LastModified.'),
    sa.Column('project_installation_number', sa.Text(), nullable=True, comment='3API attributes.projectInstallationNumber (nullable).'),
    sa.Column('completion_status', sa.Text(), nullable=True, comment='Eine Spalte für 3API attributes.state, knxproj CompletionStatus und TTL core:state. XML-Omit = Undefined.'),
    sa.Column('type_description', sa.Text(), nullable=True, comment='3API item.meta.typedescription (uri, optional).'),
    sa.Column('master_data_version', sa.Integer(), nullable=True, comment='Kategorie 3. knx_master MasterData/@Version.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint("completion_status IS NULL OR completion_status IN ('Undefined', 'Editing', 'FinishedDesign', 'FinishedCommissioning', 'Tested', 'Accepted')", name=op.f('ck_installation_versions_completion_status')),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_installation_versions_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('installation_id', '_since', name=op.f('pk_installation_versions'))
    )
    op.create_table('locations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='3API LocationTypeAndId.id (uuid).'),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj-Suffix BP-n. TTL prj:BP-n. Site optional ohne ets_id.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_locations_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_locations')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_locations_installation_ets_id')
    )
    op.create_index('ix_locations_installation_id', 'locations', ['installation_id'], unique=False)
    op.create_table('master_datapoint_roles',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='z. B. DR-1.'),
    sa.Column('name', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_master_datapoint_roles_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_master_datapoint_roles')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_master_datapoint_roles_installation_ets_id')
    )
    op.create_table('master_datapoint_subtypes',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='z. B. DPST-1-2.'),
    sa.Column('datapoint_type_ets_id', sa.Text(), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_master_datapoint_subtypes_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_master_datapoint_subtypes')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_master_datapoint_subtypes_installation_ets_id')
    )
    op.create_table('master_datapoint_types',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='z. B. DPT-1.'),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('size_in_bit', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_master_datapoint_types_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_master_datapoint_types')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_master_datapoint_types_installation_ets_id')
    )
    op.create_table('master_function_types',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='z. B. FT-0.'),
    sa.Column('name', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_master_function_types_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_master_function_types')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_master_function_types_installation_ets_id')
    )
    op.create_table('master_medium_types',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='z. B. MT-0.'),
    sa.Column('name', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_master_medium_types_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_master_medium_types')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_master_medium_types_installation_ets_id')
    )
    op.create_table('master_space_usages',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='z. B. SU-2.'),
    sa.Column('name', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_master_space_usages_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_master_space_usages')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_master_space_usages_installation_ets_id')
    )
    op.create_table('trades',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='KSS Kategorie 3. Stabile Gewerk-Identität (UUID, nicht 3API).'),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj-Suffix T-n. Nicht im TTL.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_trades_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trades')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_trades_installation_ets_id')
    )
    op.create_index('ix_trades_installation_id', 'trades', ['installation_id'], unique=False)
    op.create_table('area_versions',
    sa.Column('area_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('address', sa.Integer(), nullable=True, comment='Area/@Address (0–15), Teil der Individualadresse.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['area_id'], ['areas.id'], name=op.f('fk_area_versions_area_id_areas'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('area_id', '_since', name=op.f('pk_area_versions'))
    )
    op.create_table('datapoint_versions',
    sa.Column('datapoint_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('group_address', sa.Integer(), nullable=True, comment='16-Bit GroupAddress/@Address / knx:groupAddress. Anzeige aus Stil + diesem Integer, keine Haupt-/Mittelgruppe-Spalten.'),
    sa.Column('datapoint_type', postgresql.ARRAY(sa.Text()), nullable=True, comment='3API attributes.datapointType (URN/IRI).'),
    sa.Column('datapoint_subtype_ets_id', sa.Text(), nullable=True, comment='Kategorie 3. knxproj @DatapointType, z. B. DPST-1-2.'),
    sa.Column('readable', sa.Boolean(), nullable=True),
    sa.Column('writable', sa.Boolean(), nullable=True),
    sa.Column('security', sa.Text(), nullable=True, comment='Kategorie 3. GroupAddress/@Security / knx:securityMode.'),
    sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True),
    sa.Column('group_range_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Innerster GroupRange; Umhängen ist historisiert.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint('group_address IS NULL OR (group_address >= 0 AND group_address <= 65535)', name=op.f('ck_datapoint_versions_group_address')),
    sa.ForeignKeyConstraint(['datapoint_id'], ['datapoints.id'], name=op.f('fk_datapoint_versions_datapoint_id_datapoints'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['group_range_id'], ['group_ranges.id'], name=op.f('fk_datapoint_versions_group_range_id_group_ranges'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('datapoint_id', '_since', name=op.f('pk_datapoint_versions'))
    )
    op.create_index('ix_datapoint_versions_group_address', 'datapoint_versions', ['group_address'], unique=False)
    op.create_index('ix_datapoint_versions_group_range_id', 'datapoint_versions', ['group_range_id'], unique=False)
    op.create_table('device_channels',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. ChannelInstance-Fragment, z. B. CI-9 oder DI-65_CI-9.'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_device_channels_device_id_devices'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_channels')),
    sa.UniqueConstraint('device_id', 'ets_id', name='uq_device_channels_device_ets_id')
    )
    op.create_index('ix_device_channels_device_id', 'device_channels', ['device_id'], unique=False)
    op.create_table('device_folders',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. Folder RefId, z. B. PB-47.'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_device_folders_device_id_devices'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_device_folders')),
    sa.UniqueConstraint('device_id', 'ets_id', name='uq_device_folders_device_ets_id')
    )
    op.create_table('function_datapoints',
    sa.Column('function_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('datapoint_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=True, comment='Kategorie 3. GroupAddressRef/@Id, z. B. GF-1.'),
    sa.Column('role', sa.Text(), nullable=True, comment='Kategorie 3. GroupAddressRef/@Role (DR-* oder UUID). TTL hat kein Role.'),
    sa.Column('linked', sa.Boolean(), nullable=False, comment='false = Entkopplung ab diesem _since.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['datapoint_id'], ['datapoints.id'], name=op.f('fk_function_datapoints_datapoint_id_datapoints'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['function_id'], ['functions.id'], name=op.f('fk_function_datapoints_function_id_functions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('function_id', 'datapoint_id', '_since', name=op.f('pk_function_datapoints'))
    )
    op.create_index('ix_function_datapoints_datapoint_id', 'function_datapoints', ['datapoint_id'], unique=False)
    op.create_table('function_versions',
    sa.Column('function_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('function_type_ets_id', sa.Text(), nullable=True, comment='Kategorie 3. FunctionType FT-*. WA53H10 oft FT-0 (custom).'),
    sa.Column('at_type', postgresql.ARRAY(sa.Text()), nullable=True, comment='3API meta.@type; TTL core:ApplicationFunction.'),
    sa.Column('type_description', sa.Text(), nullable=True),
    sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=True, comment='3API relationships.functionLocation / loc:hasApplicationFunction.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['function_id'], ['functions.id'], name=op.f('fk_function_versions_function_id_functions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_function_versions_location_id_locations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('function_id', '_since', name=op.f('pk_function_versions'))
    )
    op.create_index('ix_function_versions_location_id', 'function_versions', ['location_id'], unique=False)
    op.create_table('group_range_versions',
    sa.Column('group_range_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('parent_group_range_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('range_start', sa.Integer(), nullable=True),
    sa.Column('range_end', sa.Integer(), nullable=True),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint('parent_group_range_id IS DISTINCT FROM group_range_id', name=op.f('ck_group_range_versions_parent_not_self')),
    sa.CheckConstraint('range_end IS NULL OR (range_end >= 0 AND range_end <= 65535)', name=op.f('ck_group_range_versions_range_end')),
    sa.CheckConstraint('range_start IS NULL OR (range_start >= 0 AND range_start <= 65535)', name=op.f('ck_group_range_versions_range_start')),
    sa.ForeignKeyConstraint(['group_range_id'], ['group_ranges.id'], name=op.f('fk_group_range_versions_group_range_id_group_ranges'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_group_range_id'], ['group_ranges.id'], name=op.f('fk_group_range_versions_parent_group_range_id_group_ranges'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('group_range_id', '_since', name=op.f('pk_group_range_versions'))
    )
    op.create_index('ix_group_range_versions_parent_group_range_id', 'group_range_versions', ['parent_group_range_id'], unique=False)
    op.create_table('lines',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. knxproj-Suffix, z. B. L-1. Nicht im TTL.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.Column('area_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.ForeignKeyConstraint(['area_id'], ['areas.id'], name=op.f('fk_lines_area_id_areas'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_lines_installation_id_installations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lines')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_lines_installation_ets_id')
    )
    op.create_index('ix_lines_area_id', 'lines', ['area_id'], unique=False)
    op.create_index('ix_lines_installation_id', 'lines', ['installation_id'], unique=False)
    op.create_table('trade_devices',
    sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('linked', sa.Boolean(), nullable=False, comment='false = Zuordnung aufgehoben ab diesem _since.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_trade_devices_device_id_devices'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], name=op.f('fk_trade_devices_trade_id_trades'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('trade_id', 'device_id', '_since', name=op.f('pk_trade_devices'))
    )
    op.create_index('ix_trade_devices_device_id', 'trade_devices', ['device_id'], unique=False)
    op.create_table('trade_versions',
    sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=False, comment='KNX-XML Trade_t/@Name. Darf projektweit kollidieren.'),
    sa.Column('number', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('completion_status', sa.Text(), nullable=True),
    sa.Column('parent_trade_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint("completion_status IS NULL OR completion_status IN ('Undefined', 'Editing', 'FinishedDesign', 'FinishedCommissioning', 'Tested', 'Accepted')", name=op.f('ck_trade_versions_completion_status')),
    sa.CheckConstraint('parent_trade_id IS DISTINCT FROM trade_id', name=op.f('ck_trade_versions_parent_not_self')),
    sa.ForeignKeyConstraint(['parent_trade_id'], ['trades.id'], name=op.f('fk_trade_versions_parent_trade_id_trades'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], name=op.f('fk_trade_versions_trade_id_trades'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('trade_id', '_since', name=op.f('pk_trade_versions'))
    )
    op.create_index('ix_trade_versions_parent_trade_id', 'trade_versions', ['parent_trade_id'], unique=False)
    op.create_table('comm_objects',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. RefId-Suffix O-…_R-…. TTL core:Datapoint (nicht GA).'),
    sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('folder_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['device_channels.id'], name=op.f('fk_comm_objects_channel_id_device_channels'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_comm_objects_device_id_devices'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['folder_id'], ['device_folders.id'], name=op.f('fk_comm_objects_folder_id_device_folders'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_comm_objects')),
    sa.UniqueConstraint('device_id', 'ets_id', name='uq_comm_objects_device_ets_id')
    )
    op.create_index('ix_comm_objects_channel_id', 'comm_objects', ['channel_id'], unique=False)
    op.create_index('ix_comm_objects_device_id', 'comm_objects', ['device_id'], unique=False)
    op.create_table('device_channel_versions',
    sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('catalog_ref', sa.Text(), nullable=True, comment='Kategorie 3. ChannelInstance/@RefId, z. B. CH-3 oder MD-…_CH-4.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['channel_id'], ['device_channels.id'], name=op.f('fk_device_channel_versions_channel_id_device_channels'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('channel_id', '_since', name=op.f('pk_device_channel_versions'))
    )
    op.create_table('device_folder_versions',
    sa.Column('folder_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('parent_folder_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint('parent_folder_id IS DISTINCT FROM folder_id', name=op.f('ck_device_folder_versions_parent_not_self')),
    sa.ForeignKeyConstraint(['folder_id'], ['device_folders.id'], name=op.f('fk_device_folder_versions_folder_id_device_folders'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_folder_id'], ['device_folders.id'], name=op.f('fk_device_folder_versions_parent_folder_id_device_folders'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('folder_id', '_since', name=op.f('pk_device_folder_versions'))
    )
    op.create_table('line_versions',
    sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('address', sa.Integer(), nullable=True, comment='Line/@Address (0–15), Teil der Individualadresse.'),
    sa.Column('medium_type_ets_id', sa.Text(), nullable=True, comment='Kategorie 3. MediumTypeRefId, z. B. MT-0.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['line_id'], ['lines.id'], name=op.f('fk_line_versions_line_id_lines'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('line_id', '_since', name=op.f('pk_line_versions'))
    )
    op.create_table('location_versions',
    sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False, comment='FK zur stabilen Orts-Identität.'),
    sa.Column('title', sa.Text(), nullable=False, comment='3API attributes.title. Synthetisches Site-Dummy nicht als echte Daten behandeln.'),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('number', sa.Text(), nullable=True, comment='Kategorie 3. Space/@Number.'),
    sa.Column('location_type', sa.Text(), nullable=True, comment='Kategorie 3. Space/@Type (SpaceType_t).'),
    sa.Column('usage', sa.Text(), nullable=True, comment='Kategorie 3. Space/@Usage (SU-* oder tag:bedroom).'),
    sa.Column('completion_status', sa.Text(), nullable=True, comment='CompletionStatus / core:state.'),
    sa.Column('at_type', postgresql.ARRAY(sa.Text()), nullable=True, comment='3API item.meta.@type (z. B. loc:Building, loc:Site).'),
    sa.Column('type_description', sa.Text(), nullable=True),
    sa.Column('parent_location_id', postgresql.UUID(as_uuid=True), nullable=True, comment='3API relationships.parentLocation. NULL = Wurzel.'),
    sa.Column('default_line_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Kategorie 3. Space/@DefaultLine → lines.id.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint("completion_status IS NULL OR completion_status IN ('Undefined', 'Editing', 'FinishedDesign', 'FinishedCommissioning', 'Tested', 'Accepted')", name=op.f('ck_location_versions_completion_status')),
    sa.CheckConstraint("location_type IS NULL OR location_type IN ('Building', 'BuildingPart', 'Floor', 'Room', 'DistributionBoard', 'Stairway', 'Corridor', 'Area', 'Ground', 'Segment')", name=op.f('ck_location_versions_location_type')),
    sa.CheckConstraint('parent_location_id IS DISTINCT FROM location_id', name=op.f('ck_location_versions_parent_not_self')),
    sa.ForeignKeyConstraint(['default_line_id'], ['lines.id'], name=op.f('fk_location_versions_default_line_id_lines'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_location_versions_location_id_locations'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_location_id'], ['locations.id'], name=op.f('fk_location_versions_parent_location_id_locations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('location_id', '_since', name=op.f('pk_location_versions'))
    )
    op.create_index('ix_location_versions_default_line_id', 'location_versions', ['default_line_id'], unique=False)
    op.create_index('ix_location_versions_parent_location_id', 'location_versions', ['parent_location_id'], unique=False)
    op.create_table('segments',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('installation_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('ets_id', sa.Text(), nullable=False, comment='Kategorie 3. knxproj-Suffix, z. B. S-1. Nicht im TTL.'),
    sa.Column('puid', sa.Integer(), nullable=True),
    sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.ForeignKeyConstraint(['installation_id'], ['installations.id'], name=op.f('fk_segments_installation_id_installations'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['line_id'], ['lines.id'], name=op.f('fk_segments_line_id_lines'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_segments')),
    sa.UniqueConstraint('installation_id', 'ets_id', name='uq_segments_installation_ets_id')
    )
    op.create_index('ix_segments_installation_id', 'segments', ['installation_id'], unique=False)
    op.create_index('ix_segments_line_id', 'segments', ['line_id'], unique=False)
    op.create_table('comm_object_datapoints',
    sa.Column('comm_object_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('datapoint_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('linked', sa.Boolean(), nullable=False, comment='false = Entkopplung ab diesem _since.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['comm_object_id'], ['comm_objects.id'], name=op.f('fk_comm_object_datapoints_comm_object_id_comm_objects'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['datapoint_id'], ['datapoints.id'], name=op.f('fk_comm_object_datapoints_datapoint_id_datapoints'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('comm_object_id', 'datapoint_id', '_since', name=op.f('pk_comm_object_datapoints'))
    )
    op.create_index('ix_comm_object_datapoints_datapoint_id', 'comm_object_datapoints', ['datapoint_id'], unique=False)
    op.create_table('comm_object_versions',
    sa.Column('comm_object_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('datapoint_subtype_ets_id', sa.Text(), nullable=True),
    sa.Column('communication_flag', sa.Boolean(), nullable=True),
    sa.Column('read_flag', sa.Boolean(), nullable=True),
    sa.Column('write_flag', sa.Boolean(), nullable=True),
    sa.Column('transmit_flag', sa.Boolean(), nullable=True),
    sa.Column('update_flag', sa.Boolean(), nullable=True),
    sa.Column('read_on_init_flag', sa.Boolean(), nullable=True),
    sa.Column('priority', sa.Text(), nullable=True),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.ForeignKeyConstraint(['comm_object_id'], ['comm_objects.id'], name=op.f('fk_comm_object_versions_comm_object_id_comm_objects'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('comm_object_id', '_since', name=op.f('pk_comm_object_versions'))
    )
    op.create_table('device_versions',
    sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.Text(), nullable=False, comment='3API title. knxproj @Name wenn gesetzt, sonst Produktname.'),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('order_number', sa.Text(), nullable=True),
    sa.Column('manufacturer', sa.Text(), nullable=True),
    sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_downloaded', sa.DateTime(timezone=True), nullable=True, comment='3API lastDownloaded / LastDownload. Sentinel 0001-01-01 nicht speichern (kein echter Download).'),
    sa.Column('current_date_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('serial_number', sa.Text(), nullable=True, comment='3API serialNumber. Eine Spalte: 12 Hex-Zeichen der 6 Bytes (TTL $hex, XML Base64 → Importer wandelt).'),
    sa.Column('individual_address', sa.Text(), nullable=True, comment='3API individualAddress (z. B. 1.0.248). TTL hex ohne 0x.'),
    sa.Column('firmware_version', sa.Text(), nullable=True),
    sa.Column('hardware_version', sa.Text(), nullable=True),
    sa.Column('completion_status', sa.Text(), nullable=True, comment='CompletionStatus / core:state.'),
    sa.Column('communication_part_loaded', sa.Boolean(), nullable=True, comment='Kategorie 3. CommunicationPartLoaded. Allein kein Nachweis für LastDownload (Dummy-IP-Geräte).'),
    sa.Column('product_ref', sa.Text(), nullable=True, comment='Kategorie 3. DeviceInstance/@ProductRefId.'),
    sa.Column('application_program_ref', sa.Text(), nullable=True, comment='Kategorie 3. Hardware2Program / ApplicationProgram.'),
    sa.Column('bus_current', sa.Integer(), nullable=True),
    sa.Column('installation_hints', sa.Text(), nullable=True, comment='Kategorie 3. InstallationHints (RTF möglich).'),
    sa.Column('at_type', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('type_description', sa.Text(), nullable=True),
    sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=True, comment='3API relationships.deviceLocation.'),
    sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Kategorie 3. Device hängt am Segment (Topology).'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint("completion_status IS NULL OR completion_status IN ('Undefined', 'Editing', 'FinishedDesign', 'FinishedCommissioning', 'Tested', 'Accepted')", name=op.f('ck_device_versions_completion_status')),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_device_versions_device_id_devices'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_device_versions_location_id_locations'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], name=op.f('fk_device_versions_segment_id_segments'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('device_id', '_since', name=op.f('pk_device_versions'))
    )
    op.create_index('ix_device_versions_location_id', 'device_versions', ['location_id'], unique=False)
    op.create_index('ix_device_versions_segment_id', 'device_versions', ['segment_id'], unique=False)
    op.create_table('segment_versions',
    sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('medium_type_ets_id', sa.Text(), nullable=True, comment='Kategorie 3. MediumTypeRefId am Segment.'),
    sa.Column('_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). ETS-Projekt- bzw. Bus-wirksame Änderung. Ende = nächstes _since derselben Identität.'),
    sa.Column('_observable_since', sa.DateTime(timezone=True), nullable=False, comment='KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde (UTC, Import).'),
    sa.CheckConstraint("medium_type_ets_id IS NULL OR medium_type_ets_id <> ''", name=op.f('ck_segment_versions_medium_type_ets_id_not_empty')),
    sa.ForeignKeyConstraint(['segment_id'], ['segments.id'], name=op.f('fk_segment_versions_segment_id_segments'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('segment_id', '_since', name=op.f('pk_segment_versions'))
    )


def downgrade() -> None:
    op.drop_table('segment_versions')
    op.drop_index('ix_device_versions_segment_id', table_name='device_versions')
    op.drop_index('ix_device_versions_location_id', table_name='device_versions')
    op.drop_table('device_versions')
    op.drop_table('comm_object_versions')
    op.drop_index('ix_comm_object_datapoints_datapoint_id', table_name='comm_object_datapoints')
    op.drop_table('comm_object_datapoints')
    op.drop_index('ix_segments_line_id', table_name='segments')
    op.drop_index('ix_segments_installation_id', table_name='segments')
    op.drop_table('segments')
    op.drop_index('ix_location_versions_parent_location_id', table_name='location_versions')
    op.drop_index('ix_location_versions_default_line_id', table_name='location_versions')
    op.drop_table('location_versions')
    op.drop_table('line_versions')
    op.drop_table('device_folder_versions')
    op.drop_table('device_channel_versions')
    op.drop_index('ix_comm_objects_device_id', table_name='comm_objects')
    op.drop_index('ix_comm_objects_channel_id', table_name='comm_objects')
    op.drop_table('comm_objects')
    op.drop_index('ix_trade_versions_parent_trade_id', table_name='trade_versions')
    op.drop_table('trade_versions')
    op.drop_index('ix_trade_devices_device_id', table_name='trade_devices')
    op.drop_table('trade_devices')
    op.drop_index('ix_lines_installation_id', table_name='lines')
    op.drop_index('ix_lines_area_id', table_name='lines')
    op.drop_table('lines')
    op.drop_index('ix_group_range_versions_parent_group_range_id', table_name='group_range_versions')
    op.drop_table('group_range_versions')
    op.drop_index('ix_function_versions_location_id', table_name='function_versions')
    op.drop_table('function_versions')
    op.drop_index('ix_function_datapoints_datapoint_id', table_name='function_datapoints')
    op.drop_table('function_datapoints')
    op.drop_table('device_folders')
    op.drop_index('ix_device_channels_device_id', table_name='device_channels')
    op.drop_table('device_channels')
    op.drop_index('ix_datapoint_versions_group_range_id', table_name='datapoint_versions')
    op.drop_index('ix_datapoint_versions_group_address', table_name='datapoint_versions')
    op.drop_table('datapoint_versions')
    op.drop_table('area_versions')
    op.drop_index('ix_trades_installation_id', table_name='trades')
    op.drop_table('trades')
    op.drop_table('master_space_usages')
    op.drop_table('master_medium_types')
    op.drop_table('master_function_types')
    op.drop_table('master_datapoint_types')
    op.drop_table('master_datapoint_subtypes')
    op.drop_table('master_datapoint_roles')
    op.drop_index('ix_locations_installation_id', table_name='locations')
    op.drop_table('locations')
    op.drop_table('installation_versions')
    op.drop_index('ix_installation_subscriptions_subscription_id', table_name='installation_subscriptions')
    op.drop_index('ix_installation_subscriptions_installation_id', table_name='installation_subscriptions')
    op.drop_table('installation_subscriptions')
    op.drop_index('ix_group_ranges_installation_id', table_name='group_ranges')
    op.drop_table('group_ranges')
    op.drop_index('ix_functions_installation_id', table_name='functions')
    op.drop_table('functions')
    op.drop_index('ix_devices_installation_id', table_name='devices')
    op.drop_table('devices')
    op.drop_index('ix_datapoints_installation_id', table_name='datapoints')
    op.drop_table('datapoints')
    op.drop_index('ix_datafields_installation_id', table_name='datafields')
    op.drop_table('datafields')
    op.drop_index('ix_areas_installation_id', table_name='areas')
    op.drop_table('areas')
    op.drop_index('ix_installations_knx_project_id', table_name='installations')
    op.drop_table('installations')
