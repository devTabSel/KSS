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

# XSD 23 simpleType ProjectType_t (Project Schema Documentation 01.00.00).
# XML token = English enumeration value, e.g. "Family House".
# Default if the attribute is omitted: Other (Commercial).
PROJECT_TYPE_VALUES = (
    "Apartment",
    "Family House",
    "Villa",
    "Other (Residential)",
    "Hotel",
    "Airport",
    "Office Building",
    "Educational",
    "Leisure",
    "Entertainment",
    "Public Building",
    "Health Care",
    "Other (Commercial)",
    "Manufacturer",
    "City Project",
    "Transportation",
    "Other (Other)",
)

_PROJECT_TYPE_IN = ", ".join(f"'{value}'" for value in PROJECT_TYPE_VALUES)

PROJECT_TYPE_SQL = f"project_type IS NULL OR project_type IN ({_PROJECT_TYPE_IN})"

MASTER_PROJECT_TYPE_ETS_ID_SQL = f"ets_id IN ({_PROJECT_TYPE_IN})"

# ETS Language/@Identifier (de-DE, en-US) or shorter KIM tags (@en → en).
LANGUAGE_CODE_SQL = "char_length(btrim(language_code)) >= 2"

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
