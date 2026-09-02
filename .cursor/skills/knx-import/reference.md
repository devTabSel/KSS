# Import → Tabellen

Beide Exporte füllen dieselben Zeilen. `ets_id` = TTL-Fragment = knxproj-Suffix.

## Installation

- Identity: `project_guid`, `knx_project_id` (`P-040E`), `installation_index` (`0`), `ets_id` (`P-040E-0`), `group_address_style` (einmal, nicht versionieren), `last_import` (PATCH-Ingest).
- Version: `title` ← ProjectInformation/@Name; `completion_status` ← ProjectInformation/@CompletionStatus (= TTL `core:state`, 3API `state`); `last_modified` (PK-Teil); `comment` (RTF möglich); `master_data_version` ← knx_master `MasterData/@Version`.
- Katalog (current-state, installationsbezogen, nicht temporal): DPT, DPST, Format-Felder = 3API datafield (`ets_id` z. B. `DPST-1-2_F-1` / TTL `knx:type.dpt.field.1.2.i0`); FunctionType `FT-*`; DatapointRole `DR-*`; SpaceUsage `SU-*`; MediumType `MT-*`.

## Location

- `location_type` ← `Space/@Type` (XSD, nicht knx_master): Building, BuildingPart, Floor, Room, DistributionBoard, Stairway, Corridor, Area, Ground, Segment.
- `usage` ← `@Usage` (`SU-2` oder `tag:bedroom`).
- `number`, `description`, `completion_status`, `parent_location_id`, `default_line_id`.
- TTL: `loc:BuildingPart` → type BuildingPart / `loc:Space`; `tag:hasLocationUsage`; `loc:hasApplicationFunction` → functions.

ETS-Funktion: `functions.ets_id` `F-n`, Klasse `core:ApplicationFunction`. `function_datapoints` temporal inkl. `role` (`GroupAddressRef/@Role`) und `ets_id` `GF-*`. TTL nur `knx:hasFunctionPoint` (kein Role).

## Device

- 3API-Felder plus `completion_status`, `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded`, `product_ref`, `application_program_ref`, `bus_current`, `location_id`, `segment_id`, `installation_hints`.
- Serial: eine Hex-Spalte (TTL `$00…` / XML Base64).
- Channel: `ChannelInstance/@Id` + `catalog_ref`; Folder `PB-*`; CommObject `RefId` `O-…_R-…` temporal (DPT/Flags/Text).
- `comm_object_datapoints`: XML `@Links` / TTL `core:groups` (Inverse). Unlink = neue Zeile `linked=false`.
- BUS-Indizes: `bus_pa_bindings`, `bus_ga_bindings` (materialisiert beim Import).

## Datapoint (= GA)

- Identity bleibt bei Adressänderung (`GA-17296`). Version: `group_address` Integer, `title`, DPT, security, readable/writable, `group_range_id`.
- `group_ranges` temporal (Name/Parent/Range). Stil nur an Installation; Anzeige aus Integer + Stil.
- Keine DPT-Form-Spalten auf der GA (unit/enum/min/max → datafields).

## Trade / Topology

- Trade: `T-n`, Name darf kollidieren; Zuordnung Device temporal (`linked`).
- Area/Line/Segment nur knxproj; Device.segment_id; IA am Device denormalisiert.

## `last_modified` (Kurz)

| Ereignis | `last_modified` |
| --- | --- |
| Anlegen / Änderung | Objekt-`LastModified`, sonst Projekt-`LastModified` |
| Neue Version | nur bei semantischem Diff |
| PK | `(entity_id, last_modified)` |

Import-Uhr: `installations.last_import`. BUS: `bus_pa_bindings`, `bus_ga_bindings` — siehe `plans/temporal-bus-semantics.md`.

Telegramm zur Zeit x: BUS-Indizes nach `last_downloaded`, dann `E(entity, x) = max(last_modified) <= x`.
