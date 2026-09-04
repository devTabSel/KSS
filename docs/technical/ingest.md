# Ingest

`PATCH /api/kss/installations` — Collection, multipart. Handler: `src/kss/api/installations.py`.

| Suffix | Service | 201 / 204 | Ablehnung |
| --- | --- | --- | --- |
| `.knxproj` | `kss.services.knxproj` + Paket-upserts | neu / Reimport | 422 `KnxprojImportError`; Schema ≠ 23 |
| `.ttl` | `kss.services.ttl` (`parse_ttl` / `ingest_ttl`) | neu / Reimport | 422 `TtlImportError` (Müll, unlesbar, Mapping) |
| sonst | — | — | 422 `supported now: .knxproj, .ttl` |

Kein Body. Lookup immer über `project_guid`. Gleiche GUID aus knxproj und TTL = eine Installation. `last_import` = Import-UTC.

Passwort und `Accept-Language` nur knxproj (kein knx_master-Overlay im TTL).

Datei-GET (Stand zu `t`): [export.md](export.md).

## Ablauf knxproj

1. Fork `devTabSel/xknxproject`: `XKNXProj.parse(combine=False, more_info=True, include_catalog=True)` in `kss/services/knxproj.py`. `combine=False` = keine DPT-Inferenz. `more_info=True` = additive Keys (`ets_id`, extra `info`, GOT, `comm_objects`, Segmente, Trades, …). `include_catalog=True` = Top-Level `master_data` und `manufacturer_data`. Default-`parse()` bleibt das HA-Dict (kein Katalog).
2. `upsert_master_catalog`, dann `upsert_manufacturer_catalog`, dann `upsert_installation_from_info` aus `info`.
3. Dieselbe PATCH-Session: Topology, Locations, Devices, Device-Parts, Datapoints, CO↔GA, BUS-Indizes, Trades.
4. Neue Version nur bei semantischem Diff; `last_modified` aus ETS.

Installation-`info` bei `more_info=True`: bestehende HA-Keys plus `installation_index`, `ets_id`, `completion_status` (XML-Omit → `Undefined`), `comment`, `master_data_version`, `project_number`, `contract_number`, `project_type` (XML-Token). Leer/Omit → `null`. Sprachlabels (`Familienhaus`) nicht erfinden. `master_data` und `manufacturer_data` kommen nur mit `include_catalog=True`, nicht über `info`. `upsert_manufacturer_catalog` ist insert-if-missing (kein Update bestehender `knx_id`).

## Ablauf TTL

ETS Semantic Export oder KSS-Turtle (KIM-RDF). Abhängigkeit `rdflib` in `pyproject.toml`. Ruft **nicht** `upsert_installation_from_info` auf (kein Schema-23; knxproj-only Spalten bleiben beim Join). `parse_ttl` verlangt einen Instanzblock, der mit `prj:` beginnt (Truncation vor dem Ontologie-Dump).

1. `@prefix prj: <http://iot.knx.org/{guid}#>` → `project_guid`.
2. Nur `prj:`-Individuals; Truncation vor dem Ontologie-Dump (erster Non-`prj:`-CURIE in Spalte 0, z. B. `dct:available`).
3. Join-Schlüssel wie knxproj: `project_guid` + Fragment `P-…`, `BP-n`, `DI-n`, `F-n`, `GA-n`, `T-n`.
4. Persistiert: Installation, Locations (ohne `prj:Site`), Functions (`core:ApplicationFunction`), Devices (`core:Device` only), Datapoints (`knx:FunctionPoint` / `GA-n` only), `function_datapoints` aus `knx:hasFunctionPoint`, **`prj:T-*` Trades und `knx:hasDevice` → `trades` / `trade_devices`**.
5. Device: `assigned_trade` ← `mac:assignedTrade`, `operates_for_trade` ← `tag:operatesForTrade`; IA Hex→dotted; Serial `$hex` → Base64 wie knxproj `@SerialNumber` (Omit/leer → NULL); Sentinel `0001-01-01` `lastDownloaded` nicht gespeichert (Importer). Product-Katalog insert-if-missing aus `core:hasProduct` + `core:orderNumber`/`core:manufacturer` (`master_products`); nicht auf DeviceVersion.

ETS Semantic Export hat typischerweise keine `prj:T-*` → 0 Trades (`tests/test_ttl.py`). KSS-exportiertes `.ttl` enthält `prj:T-*` und roundtrippt (`tests/test_export_roundtrip.py`).

Preserve, wenn TTL `None` liefert und schon eine knxproj-Version existiert:

| Paket | Felder |
| --- | --- |
| Installation | `contract_number`, `project_installation_number`, `project_type`, `master_data_version`, `schema_version`, `created_by`, `ip_routing_backbone_key`, `bcu_key`, `group_address_style` |
| Location | `default_line_id` |
| Device | Loaded-Flags, `segment_id` |
| Datapoint | `datapoint_subtype_ets_id`, `group_range_id` |

Nicht aus TTL: Topology `A-*`/`L-*`/`S-*`, Channels/Folders/COs, BUS, GroupRange, knx_master, voller Hersteller-XML-Katalog (Hardware/HP/ApplicationProgram — TTL nur Product insert-if-missing), `core:Functionality`, `core:Datapoint` (COs) als Datapoints, `prj:Site`. Fehlende Entities werden nicht unlinked. Kein Auto-Join `mac:assignedTrade` → `trades.T-n`. JSON-LD-Ingest fehlt.

## Nicht umschlüsseln

Locations nicht nach Name, Devices nicht nach Individualadresse. Fehlende Parser-Keys gehören in den xknxproject-Fork (`parse(more_info=True)`).
