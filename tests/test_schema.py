from sqlalchemy import Integer, inspect

from kss.models.datapoint import Datapoint, DatapointVersion, GroupRangeVersion
from kss.models.device import (
    Device,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceFolderVersion,
    DeviceVersion,
)
from kss.models.installation import Installation, InstallationVersion
from kss.models.master import MasterProjectType
from kss.models.location import Function, FunctionDatapoint, FunctionVersion, LocationVersion
from kss.models.trade import TradeDevice, TradeVersion


def test_installation_identity_holds_join_keys() -> None:
    columns = {column.name for column in inspect(Installation).columns}
    assert columns == {
        "id",
        "ets_id",
        "project_guid",
        "last_import",
        "project_start",
        "language_code",
    }
    version = {column.name for column in inspect(InstallationVersion).columns}
    assert "state" not in version
    assert "completion_status" in version
    assert "master_data_version" in version
    assert "project_type" in version
    assert "group_address_style" in version
    assert "project_installation_number" in version
    assert "contract_number" in version
    assert "comment" in version


def test_master_project_type_is_language_aware_catalog() -> None:
    columns = {column.name for column in inspect(MasterProjectType).columns}
    assert columns == {
        "id",
        "ets_id",
        "language_code",
        "name",
    }
    assert "project_type" not in {c.name for c in inspect(Installation).columns}


def test_device_identity_and_trade_ttl_fields() -> None:
    identity = {column.name for column in inspect(Device).columns}
    version = {column.name for column in inspect(DeviceVersion).columns}
    assert identity == {"id", "installation_id", "ets_id"}
    assert "assigned_trade" in version
    assert "operates_for_trade" in version
    assert "location_id" in version
    assert "segment_id" in version
    assert "communication_part_loaded" in version
    assert "individual_address_loaded" in version
    assert "application_program_loaded" in version
    assert "parameters_loaded" in version
    assert "medium_config_loaded" in version
    assert "completion_status" in version
    assert "valid_to" not in version


def test_datapoint_stores_integer_group_address() -> None:
    version = {column.name for column in inspect(DatapointVersion).columns}
    assert "group_address" in version
    assert "name" in version
    assert "title" not in version
    assert "datapoint_type" not in version
    assert "purpose" in version
    assert "global" in version
    assert "key" in version
    assert "value" not in version
    ga = inspect(DatapointVersion).columns["group_address"]
    assert isinstance(ga.type, Integer)
    identity = {column.name for column in inspect(Datapoint).columns}
    assert {"id", "installation_id", "ets_id"} == identity
    range_version = {column.name for column in inspect(GroupRangeVersion).columns}
    assert {"unfiltered", "completion_status", "security"} <= range_version


def test_function_lives_with_location_and_has_temporal_datapoint_link() -> None:
    assert "location_id" in {c.name for c in inspect(FunctionVersion).columns}
    assert "function_type_ets_id" in {c.name for c in inspect(FunctionVersion).columns}
    link = {c.name for c in inspect(FunctionDatapoint).columns}
    assert link == {
        "function_id",
        "datapoint_id",
        "last_modified",
        "ets_id",
        "role",
        "linked",
    }
    assert {c.name for c in inspect(Function).columns} == {
        "id",
        "installation_id",
        "ets_id",
    }
    assert "completion_status" in {c.name for c in inspect(FunctionVersion).columns}


def test_location_has_xsd_type_usage_and_default_line() -> None:
    version = {c.name for c in inspect(LocationVersion).columns}
    assert {
        "location_type",
        "usage",
        "number",
        "default_line_id",
        "completion_status",
        "parent_location_id",
    } <= version


def test_group_object_tree_parent_edges_on_channel_and_folder() -> None:
    folder_version = {c.name for c in inspect(DeviceFolderVersion).columns}
    assert "parent_folder_id" in folder_version
    assert "parent_channel_id" in folder_version
    channel_version = {c.name for c in inspect(DeviceChannelVersion).columns}
    assert "parent_channel_id" in channel_version
    assert "catalog_ref" in channel_version
    assert "description" in channel_version
    assert "is_active" not in channel_version
    assert "parent_folder_id" not in channel_version
    channel_identity = {c.name for c in inspect(DeviceChannel).columns}
    assert channel_identity == {"id", "device_id", "ets_id"}


def test_trade_device_is_temporal() -> None:
    columns = {c.name for c in inspect(TradeDevice).columns}
    assert columns == {
        "trade_id",
        "device_id",
        "last_modified",
        "linked",
    }
    assert "id" not in columns
    assert "completion_status" in {c.name for c in inspect(TradeVersion).columns}
