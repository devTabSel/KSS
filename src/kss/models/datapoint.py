"""Temporary re-export. Prefer ``kss.models.group_address``.

Kept so existing ``from kss.models.datapoint import Datapoint`` imports
continue to work while APIler/services follow the GroupAddress rename.
"""

from kss.models.group_address import (
    Datapoint,
    DatapointVersion,
    GroupAddress,
    GroupAddressVersion,
    GroupRange,
    GroupRangeVersion,
)

__all__ = [
    "Datapoint",
    "DatapointVersion",
    "GroupAddress",
    "GroupAddressVersion",
    "GroupRange",
    "GroupRangeVersion",
]
