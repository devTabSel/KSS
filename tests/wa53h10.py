from pathlib import Path
import zipfile

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEV_ROOT = Path(__file__).resolve().parents[2]
WA53H10_KNXPROJ = WORKSPACE_ROOT / "research" / "WA53H10.knxproj"
XKNX_RESOURCES = DEV_ROOT / "xknxproject" / "test" / "resources"
ETS6_FREE_KNXPROJ = XKNX_RESOURCES / "ets6_free.knxproj"

WA53H10_GUID = "666d92fe-6df1-445e-8c0a-a9be732a8c3f"
WA53H10_ETS_ID = "P-040E-0"
WA53H10_PROJECT_ID = "P-040E"

MINIMAL_0_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="http://knx.org/xml/project/23">
  <Project Id="P-040E">
    <Installations>
      <Installation Name="" BCUKey="4294967295" IPRoutingBackboneKey="">
        <GroupAddresses>
          <GroupRanges/>
        </GroupAddresses>
        <Topology/>
        <Locations/>
      </Installation>
    </Installations>
  </Project>
</KNX>
"""

WA53H10_INFO = {
    "project_id": WA53H10_PROJECT_ID,
    "name": "WA53H10",
    "last_modified": "2026-08-07T08:28:38.5200407Z",
    "group_address_style": "ThreeLevel",
    "guid": WA53H10_GUID,
    "schema_version": "23",
    "installation_index": 0,
    "ets_id": WA53H10_ETS_ID,
    "completion_status": "Editing",
    "comment": r"{\rtf1\ansi\test}",
    "master_data_version": 285,
    "project_number": None,
    "contract_number": None,
    "project_type": "Family House",
    "created_by": "ETS6",
    "tool_version": "6.4.8718.0",
    "language_code": "de-DE",
    "project_start": "2021-12-03T11:17:25.5406033Z",
    "bcu_key": "4294967295",
    "ip_routing_backbone_key": None,
}


def write_wa53h10_installation_knxproj(dest: Path) -> Path:
    """knxproj with WA53H10 project.xml + knx_master, without manufacturer apps."""
    with zipfile.ZipFile(WA53H10_KNXPROJ) as source, zipfile.ZipFile(
        dest, "w"
    ) as target:
        for info in source.infolist():
            name = info.filename.replace("\\", "/")
            if name == "knx_master.xml":
                target.writestr(info, source.read(info))
            elif name.startswith("P-040E") and not name.startswith("P-040E/"):
                target.writestr(info, source.read(info))
            elif name == "P-040E/project.xml":
                target.writestr(info, source.read(info))
        target.writestr("P-040E/0.xml", MINIMAL_0_XML)
    return dest
