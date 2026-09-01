"""Gemeinsame Check-Werte (XSD 23 / 3API, nicht erfunden)."""

COMPLETION_STATUS_VALUES = (
    "Undefined",
    "Editing",
    "FinishedDesign",
    "FinishedCommissioning",
    "Tested",
    "Accepted",
)

COMPLETION_STATUS_SQL = (
    "completion_status IS NULL OR completion_status IN ("
    "'Undefined', 'Editing', 'FinishedDesign', "
    "'FinishedCommissioning', 'Tested', 'Accepted')"
)

GROUP_ADDRESS_STYLE_VALUES = ("ThreeLevel", "TwoLevel", "Free")

GROUP_ADDRESS_STYLE_SQL = (
    "group_address_style IS NULL OR group_address_style IN "
    "('ThreeLevel', 'TwoLevel', 'Free')"
)

# knxproj SpaceType_t — nicht knx_master, nicht KIM-Klassen allein.
LOCATION_TYPE_VALUES = (
    "Building",
    "BuildingPart",
    "Floor",
    "Room",
    "DistributionBoard",
    "Stairway",
    "Corridor",
    "Area",
    "Ground",
    "Segment",
)

LOCATION_TYPE_SQL = (
    "location_type IS NULL OR location_type IN ("
    "'Building', 'BuildingPart', 'Floor', 'Room', 'DistributionBoard', "
    "'Stairway', 'Corridor', 'Area', 'Ground', 'Segment')"
)

DATAFIELD_KIND_VALUES = ("enum", "numbered", "datetime", "string")

DATAFIELD_KIND_SQL = (
    "kind IS NULL OR kind IN ('enum', 'numbered', 'datetime', 'string')"
)
