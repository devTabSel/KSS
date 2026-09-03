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
          <GroupRanges>
            <GroupRange Id="P-040E-0_GR-1" Name="Licht" RangeStart="256" RangeEnd="511">
              <GroupAddress Id="P-040E-0_GA-1" Address="256" Name="Licht schalten" DatapointType="DPST-1-1" Puid="1"/>
            </GroupRange>
          </GroupRanges>
        </GroupAddresses>
        <Topology>
          <Area Id="P-040E-0_A-1" Address="0" Name="_IP" CompletionStatus="Accepted" Description="">
            <Line Id="P-040E-0_L-1" Address="0" CompletionStatus="Accepted">
              <Segment Id="P-040E-0_S-1" Name="Main segment" Number="0" MediumTypeRefId="MT-5">
                <DeviceInstance Id="P-040E-0_DI-1" Address="1" Name="UGTS_DPS1280" ProductRefId="M-00A6_H-00000026-1_P-1173" Hardware2ProgramRefId="M-00A6_H-00000026-1_HP-0026-10-39D6" CompletionStatus="Accepted" SerialNumber="AKYmAAR/" CommunicationPartLoaded="true" IndividualAddressLoaded="true" ApplicationProgramLoaded="true" ParametersLoaded="true" MediumConfigLoaded="true" LastModified="2026-06-11T06:43:31.8793081Z" LastDownload="2026-06-11T06:45:07.5603833Z" Puid="35">
                  <ComObjectInstanceRefs>
                    <ComObjectInstanceRef RefId="O-1_R-1" ChannelId="CH-1" DatapointType="DPST-1-1" Links="GA-1"/>
                    <ComObjectInstanceRef RefId="O-2_R-2" ChannelId="CH-1" ReadFlag="Enabled"/>
                  </ComObjectInstanceRefs>
                  <ChannelInstances>
                    <ChannelInstance Id="P-040E-0_DI-1_CI-1" Name="Versorgung" Description="Netzteil" RefId="CH-1"/>
                  </ChannelInstances>
                  <GroupObjectTree>
                    <Nodes>
                      <Node Type="Channel" RefId="CH-1" GroupObjectInstances="O-1_R-1 O-2_R-2">
                        <Nodes>
                          <Node Type="Folder" RefId="PB-1" GroupObjectInstances="O-2_R-2"/>
                        </Nodes>
                      </Node>
                      <Node Type="Channel" RefId="CH-UCT"/>
                    </Nodes>
                  </GroupObjectTree>
                </DeviceInstance>
              </Segment>
            </Line>
          </Area>
          <Area Id="P-040E-0_A-4" Address="1" Name="TP" CompletionStatus="Accepted" Description="KNX">
            <Line Id="P-040E-0_L-5" Address="0" Name="Main">
              <Segment Id="P-040E-0_S-5" Name="Main segment" Number="0" MediumTypeRefId="MT-0"/>
            </Line>
          </Area>
        </Topology>
        <Locations>
          <Space Type="Building" DefaultLine="P-040E-0_L-1" Id="P-040E-0_BP-1" Name="00_SYS" Number="00" Puid="3">
            <Space Type="Room" DefaultLine="P-040E-0_L-5" Usage="tag:office" Id="P-040E-0_BP-4" Name="11_UGH" Number="11" Puid="14">
              <DeviceInstanceRef RefId="P-040E-0_DI-1"/>
              <Function Id="P-040E-0_F-1" Name="CTL_HEC_EGD" Type="FT-0" Puid="20568">
                <GroupAddressRef Id="P-040E-0_GF-1" RefId="P-040E-0_GA-1" Role="DR-1"/>
              </Function>
            </Space>
          </Space>
        </Locations>
        <Trades>
          <Trade Id="P-040E-0_T-14" Name="BUS" Description="KNX Bus" CompletionStatus="Accepted" Puid="2183">
            <Trade Id="P-040E-0_T-46" Name="BUS_DPS1280" Description="Enertex Dual Power Supply 1280" CompletionStatus="Accepted" Puid="5074">
              <DeviceInstanceRef RefId="P-040E-0_DI-1"/>
            </Trade>
          </Trade>
        </Trades>
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
