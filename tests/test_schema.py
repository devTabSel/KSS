from sqlalchemy import inspect

from kss.models.datapoint import Datapoint, DatapointVersion, GroupRangeVersion
from kss.models.device import Device, DeviceVersion
from kss.models.installation import Installation, InstallationVersion
from kss.models.location import Function, FunctionDatapoint, FunctionVersion, LocationVersion
from kss.models.trade import TradeDevice, TradeVersion


def test_installation_identity_holds_immutable_style_and_join_keys() -> None:
    columns = {column.name for column in inspect(Installation).columns}
    assert columns == {
        "id",
        "ets_id",
        "project_guid",
        "knx_project_id",
        "installation_index",
        "group_address_style",
    }
    version = {column.name for column in inspect(InstallationVersion).columns}
    assert "state" not in version
    assert "completion_status" in version
    assert "master_data_version" in version
    assert "group_address_style" not in version


def test_device_has_no_assigned_trade_column() -> None:
    identity = {column.name for column in inspect(Device).columns}
    version = {column.name for column in inspect(DeviceVersion).columns}
    assert identity == {"id", "installation_id", "ets_id", "puid"}
    assert "assigned_trade" not in version
    assert "location_id" in version
    assert "segment_id" in version
    assert "communication_part_loaded" in version
    assert "completion_status" in version
    assert "valid_to" not in version


def test_datapoint_stores_integer_group_address_only() -> None:
    version = {column.name for column in inspect(DatapointVersion).columns}
    assert "group_address" in version
    assert "hauptgruppe" not in version
    assert "mittelgruppe" not in version
    assert "value" not in version
    assert "timestamp" not in version
    assert "unit" not in version
    assert "enum" not in version
    range_version = {column.name for column in inspect(GroupRangeVersion).columns}
    assert {"name", "parent_group_range_id", "range_start", "range_end"} <= range_version
    identity = {column.name for column in inspect(Datapoint).columns}
    assert {"id", "installation_id", "ets_id", "puid"} == identity


def test_function_lives_with_location_and_has_temporal_datapoint_link() -> None:
    assert "location_id" in {c.name for c in inspect(FunctionVersion).columns}
    assert "function_type_ets_id" in {c.name for c in inspect(FunctionVersion).columns}
    link = {c.name for c in inspect(FunctionDatapoint).columns}
    assert link == {
        "function_id",
        "datapoint_id",
        "_since",
        "_observable_since",
        "ets_id",
        "role",
        "linked",
    }
    assert {c.name for c in inspect(Function).columns} == {
        "id",
        "installation_id",
        "ets_id",
        "puid",
    }


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


def test_trade_device_is_temporal() -> None:
    columns = {c.name for c in inspect(TradeDevice).columns}
    assert columns == {
        "trade_id",
        "device_id",
        "_since",
        "_observable_since",
        "linked",
    }
    assert "id" not in columns
    assert "completion_status" in {c.name for c in inspect(TradeVersion).columns}
