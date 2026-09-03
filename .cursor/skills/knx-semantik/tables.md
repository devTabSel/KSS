# Import → Tabellen

Beide Exporte füllen dieselben Zeilen. `ets_id` = TTL-Fragment = knxproj-Suffix. Zeitregeln: [Temporale Semantik](../../plans/temporal-bus-semantics.md).

## Installation

- Identity: `project_guid`, `knx_project_id` (`P-040E`), `installation_index` (`0`), `ets_id` (`P-040E-0`), `group_address_style` (einmal, nicht versionieren), `last_import` (PATCH-Ingest).
- Version: `title` ← ProjectInformation/@Name; `completion_status` ← ProjectInformation/@CompletionStatus (= TTL `core:state`, 3API `state`); `last_modified` (PK-Teil); `comment` (RTF möglich); `master_data_version` ← knx_master `MasterData/@Version`; `project_type` (XML-Token).
- Katalog (current-state, installationsbezogen): DPT, DPST, Format = 3API datafield; FunctionType `FT-*`; DatapointRole `DR-*`; SpaceUsage `SU-*`; MediumType `MT-*`.

## Location

- `location_type` ← `Space/@Type` (XSD, nicht knx_master).
- `usage` ← `@Usage` (`SU-2` oder `tag:bedroom`).
- `number`, `description`, `completion_status`, `parent_location_id`, `default_line_id`.
- ETS-Funktion: `functions.ets_id` `F-n`, `core:ApplicationFunction`. `function_datapoints` temporal inkl. `role`.

## Device

- 3API plus `completion_status`, fünf `*Loaded`-Flags, `product_ref`, `application_program_ref`, `bus_current`, `location_id`, `segment_id`, `installation_hints`.
- Serial: eine Hex-Spalte.
- Channel / Folder / CommObject / `comm_object_datapoints` (`linked`).
- BUS-Indizes: `bus_pa_bindings`, `bus_ga_bindings` (knxproj-PATCH nach CO↔GA; kein GET).

## Datapoint (= GA)

- Identity bleibt bei Adressänderung. Version: `group_address` Integer, `title`, DPT, security, `group_range_id`.
- `group_ranges` temporal. Stil nur an Installation.

## Trade / Topology

- Trade (knxproj): `T-n`, Name darf kollidieren; `trade_devices` temporal. TTL erzeugt **keine** Trade-Zeilen.
- TTL am Device: `mac:assignedTrade` (String, kein FK); `tag:operatesForTrade` am tragenden Subjekt. Kein Auto-Join. Plan: [Trades](../../plans/trades.md).
- Area/Line/Segment nur knxproj; Device.segment_id.

## `last_modified` (Kurz)

| Ereignis | `last_modified` |
| --- | --- |
| Anlegen / Änderung | Objekt-`LastModified`, sonst Projekt-`LastModified` |
| Neue Version | nur bei semantischem Diff |
| PK | `(entity_id, last_modified)` |

Telegramm zur Zeit x: BUS-Indizes nach `last_downloaded`, dann `E(entity, x)`.
