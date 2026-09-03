# xknxproject — Lücken und nächste Keys

Parser-Output ist ein `KNXProject`-Dict. KSS mappt ihn; dieser Skill ändert nur den Fork.

## Interne Ids vs. Dict-Keys

Der Fork kennt knxproj-`@Id` intern (`DeviceInstance.identifier`, `XMLSpace.identifier`, `XMLGroupAddress.identifier`). `_transform()` liefert das HA-Dict; `attach_more_info()` (nur `parse(more_info=True)`) setzt die Ids auf die öffentlichen Objekte. Dict-Keys bleiben IA bzw. Name — für KSS unbrauchbar als Identität, deshalb additive `ets_id`.

Bereits im Fork (Space/Function/Topology/Device/GA/GR/Trade, nur `parse(more_info=True)`):

- Space: `ets_id` (`BP-n`, Suffix von `@Id`), `comment`, `completion_status` (omit → `null`, kein `Undefined`), `last_modified` (omit → `null`), `default_line` (Suffix von `@DefaultLine`, omit → `null`). Dict-Key bleibt Name.
- Function: `ets_id` (= `identifier` `F-n`), `description`, `comment`, `completion_status`, `last_modified` (leer/omit → `null`). Function-`group_addresses`: `identifier`, `ets_id` (`GF-n`), `ga_ets_id` (`GA-n`).
- Area/Line/Segment: `ets_id` (`A-n`/`L-n`/`S-n`), `identifier`, `address` (Area/Line), `completion_status`, `last_modified` (omit → `null`). Line: `medium_type_ref` (`MT-*`) plus bestehendes `medium_type` (HA-Text); `segments` als Liste aller Segment-Objekte. Dict-Keys bleiben Area-/Line-Address.
- Device: `ets_id` (`DI-n`), `identifier`, `comment`, `completion_status`, `last_modified`, `product_ref`, `hardware_program_ref`, `installation_hints`, `segment_ets_id`. Upstream (gleiche Werte wie XKNX): `serial_number` roh Base64 Omit `""`; `last_download` roh `@LastDownload` (Sentinel-String bleibt; Drop ist KSS-Importer); `*Loaded` `== "true"` Omit → `false` (Importer: fehlend/None → False). Dict-Key bleibt Individualadresse. Geräte ohne IA weiterhin nicht im Dict. Additive `group_object_tree` (alle GOT-Channels inkl. leer/nested, Folders `PB-*`, ChannelInstance-Join `DI-n_CI-n`) und `comm_objects` (alle COs keyed `O-…_R-…`, auch ohne Links). HA-`channels` und Top-Level-`communication_objects` unverändert (nur genutzte/gelinkte). GOT/ChannelInstances nur bei `more_info=True` parsen.
- GroupAddress: `ets_id` (`GA-n`, gleich `identifier`-Suffix), `datapoint_type_ref`, `completion_status`, `last_modified`, `unfiltered`/`central`/`global_`, `purpose`/`security`, `key`. Dict-Key bleibt Display-Adresse. HA `dpt` / `data_secure` unverändert.
- GroupRange: `ets_id` (`GR-n`), `identifier` (volle `@Id`), `description`, `completion_status`, `last_modified`, `unfiltered`, `security`. Dict-Key bleibt `str_address()`.
- Trade: Top-Level `trades` keyed by `ets_id` (`T-n`); nested `trades`; `devices` = `DI-n` aus `DeviceInstanceRef`; `identifier`, `number`, `description`, `comment`, `completion_status`, `last_modified`. `_TradeLoader` nur bei `more_info=True`.

`master_data`: Top-Level-Key nur bei `parse(include_catalog=True)` (Entities + alle Languages außer en-US). Unabhängig von `more_info`. Default/HA hat den Key nicht. Keine zweite `parse()`-Methode.

## `combine` / `more_info` / `include_catalog`

`combine_project` inferiert fehlende DPT aus KO-Größe. Das ist HA-Default. KSS will das **nicht**. Extra-Keys: `more_info=True`. Katalog: `include_catalog=True`. Deshalb `parse(combine=False, more_info=True, include_catalog=True)` in `kss/services/knxproj.py`.

## Tests im Fork

Bestehende Stubs unter `test/resources/stubs/` müssen mit Default-`parse()` weiter passen (keine Extra-Keys). `assert_stub` ist exakt.

KSS-Korpus `research/`: alle `*.knxproj` für XSD (WA53H10 produktiv, Guid `666d92fe-6df1-445e-8c0a-a9be732a8c3f`; `test_A*` Reverse Engineering). TTL: alle `*.ttl`, Skill `knx-semantik`. WA53H10 optional Smoke für den Fork.
