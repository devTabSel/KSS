"""SQLAlchemy models.

Temporary aliases (until APIler/services switch): ``Datapoint`` =
``GroupAddress``, ``DatapointVersion`` = ``GroupAddressVersion``,
``FunctionDatapoint`` = ``FunctionGroupAddress``,
``CommObjectDatapoint`` = ``CommObjectGroupAddress``. Column synonym
``datapoint_id`` → ``group_address_id`` on version and edge tables.
``MasterFunctionPoint`` is the catalog ``FP-*``, not instance GAs.
KIM ``knx:FunctionPoint`` is ``at_type`` only.
"""

from kss.models.bus_bindings import BusGaBinding, BusPaBinding
from kss.models.device import (
    CommObject,
    CommObjectDatapoint,
    CommObjectGroupAddress,
    CommObjectVersion,
    Device,
    DeviceChannel,
    DeviceChannelVersion,
    DeviceFolder,
    DeviceFolderVersion,
    DeviceVersion,
)
from kss.models.group_address import (
    Datapoint,
    DatapointVersion,
    GroupAddress,
    GroupAddressVersion,
    GroupRange,
    GroupRangeVersion,
)
from kss.models.installation import Installation, InstallationSubscription, InstallationVersion
from kss.models.location import (
    Function,
    FunctionDatapoint,
    FunctionGroupAddress,
    FunctionVersion,
    Location,
    LocationVersion,
)
from kss.models.master import (
    Datafield,
    MasterApplicationCommObject,
    MasterApplicationCommObjectRef,
    MasterApplicationProgram,
    MasterData,
    MasterDatapointRole,
    MasterDatapointSubtype,
    MasterDatapointType,
    MasterFunctionPoint,
    MasterFunctionType,
    MasterHardware,
    MasterHardware2Program,
    MasterManufacturer,
    MasterMediumType,
    MasterProduct,
    MasterProjectType,
    MasterSpaceUsage,
    MasterTranslation,
)
from kss.models.topology import Area, AreaVersion, Line, LineVersion, Segment, SegmentVersion
from kss.models.trade import Trade, TradeDevice, TradeVersion

__all__ = [
    "Area",
    "AreaVersion",
    "BusGaBinding",
    "BusPaBinding",
    "CommObject",
    "CommObjectDatapoint",
    "CommObjectGroupAddress",
    "CommObjectVersion",
    "Datafield",
    "Datapoint",
    "DatapointVersion",
    "Device",
    "DeviceChannel",
    "DeviceChannelVersion",
    "DeviceFolder",
    "DeviceFolderVersion",
    "DeviceVersion",
    "Function",
    "FunctionDatapoint",
    "FunctionGroupAddress",
    "FunctionVersion",
    "GroupAddress",
    "GroupAddressVersion",
    "GroupRange",
    "GroupRangeVersion",
    "Installation",
    "InstallationSubscription",
    "InstallationVersion",
    "Line",
    "LineVersion",
    "Location",
    "LocationVersion",
    "MasterApplicationCommObject",
    "MasterApplicationCommObjectRef",
    "MasterApplicationProgram",
    "MasterData",
    "MasterDatapointRole",
    "MasterDatapointSubtype",
    "MasterDatapointType",
    "MasterFunctionPoint",
    "MasterFunctionType",
    "MasterHardware",
    "MasterHardware2Program",
    "MasterManufacturer",
    "MasterMediumType",
    "MasterProduct",
    "MasterProjectType",
    "MasterSpaceUsage",
    "MasterTranslation",
    "Segment",
    "SegmentVersion",
    "Trade",
    "TradeDevice",
    "TradeVersion",
]
