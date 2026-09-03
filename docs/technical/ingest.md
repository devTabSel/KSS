# Ingest

`PATCH /api/kss/installations` — Collection, multipart. Handler: `src/kss/api/installations.py`.

| Suffix | Service | 201 / 204 | Ablehnung |
| --- | --- | --- | --- |
| `.knxproj` | `kss.services.knxproj` + Paket-upserts | neu / Reimport | 422 `KnxprojImportError`; Schema ≠ 23 |
| `.ttl` | `kss.services.ttl` (`parse_ttl` / `ingest_ttl`) | neu / Reimport | 422 `TtlImportError` (Müll, unlesbar, Mapping) |
| sonst | — | — | 422 `supported now: .knxproj, .ttl` |

Kein Body. Lookup immer über `project_guid`. Gleiche GUID aus knxproj und TTL = eine Installation. `last_import` = Import-UTC.

Passwort und `Accept-Language` nur knxproj (kein knx_master-Overlay im TTL).

## Ablauf knxproj

1. `XKNXProj.parse(combine=False)` im Fork `devTabSel/xknxproject`.
2. `upsert_master_catalog`, dann `upsert_installation_from_info` aus `info`.
3. Dieselbe PATCH-Session: Topology, Locations, Devices, Device-Parts, Datapoints, CO↔GA, BUS-Indizes, Trades.
4. Neue Version nur bei semantischem Diff; `last_modified` aus ETS.

Installation-`info` (Fork, additiv): bestehende Keys plus `installation_index`, `ets_id`, `completion_status` (XML-Omit → `Undefined`), `comment`, `master_data_version`, `project_number`, `contract_number`, `project_type` (XML-Token). Leer/Omit → `null`. Sprachlabels (`Familienhaus`) nicht erfinden.

## Ablauf TTL

ETS Semantic Export (KIM-RDF Turtle). Abhängigkeit `rdflib` in `pyproject.toml`. Ruft **nicht** `upsert_installation_from_info` auf (kein Schema-23; knxproj-only Spalten bleiben beim Join).

1. `@prefix prj: <http://iot.knx.org/{guid}#>` → `project_guid`.
2. Nur `prj:`-Individuals; Truncation vor dem Ontologie-Dump (erster Non-`prj:`-CURIE in Spalte 0, z. B. `dct:available`).
3. Join-Schlüssel wie knxproj: `project_guid` + Fragment `P-…`, `BP-n`, `DI-n`, `F-n`, `GA-n`.
4. Persistiert: Installation, Locations (ohne `prj:Site`), Functions (`core:ApplicationFunction`), Devices (`core:Device` only), Datapoints (`knx:FunctionPoint` / `GA-n` only), `function_datapoints` aus `knx:hasFunctionPoint`.
5. Device: `assigned_trade` ← `mac:assignedTrade`, `operates_for_trade` ← `tag:operatesForTrade`; IA Hex→dotted; Serial `$hex` → Base64 wie knxproj `@SerialNumber` (Omit/leer → NULL); Sentinel `0001-01-01` `lastDownloaded` nicht gespeichert (Importer).

Preserve, wenn TTL `None` liefert und schon eine knxproj-Version existiert:

| Paket | Felder |
| --- | --- |
| Installation | `contract_number`, `project_installation_number`, `project_type`, `master_data_version`, `schema_version`, `created_by`, `ip_routing_backbone_key`, `bcu_key`, `group_address_style` |
| Location | `default_line_id` |
| Device | Loaded-Flags, `segment_id` |
| Datapoint | `datapoint_subtype_ets_id`, `group_range_id` |

Nicht aus TTL: Topology `A-*`/`L-*`/`S-*`, Trades `T-n`, Channels/Folders/COs, BUS, GroupRange, knx_master, `core:Functionality`, `core:Datapoint` (COs) als Datapoints. Fehlende Entities werden nicht unlinked. Kein Auto-Join `mac:assignedTrade` → `trades.T-n`. JSON-LD-Ingest fehlt.

## Nicht umschlüsseln

Locations nicht nach Name, Devices nicht nach Individualadresse. Fehlende Parser-Keys: Agent **Representer** (Skill `xknxproject`).
