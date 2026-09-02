# xknxproject — Lücken und nächste Keys

Parser-Output ist ein `KNXProject`-Dict. KSS mappt ihn; dieser Skill ändert nur den Fork.

## Interne Ids vs. Dict-Keys

Der Fork kennt knxproj-`@Id` intern (`DeviceInstance.identifier`, `XMLSpace.identifier`, `XMLGroupAddress.identifier`). `_transform()` wirft sie für Locations/Ranges oft weg. Dict-Keys sind heute IA bzw. Name — für KSS unbrauchbar als Identität.

Bereits im Fork (Space/Function, `parse()` immer):

- Space: `ets_id` (`BP-n`, Suffix von `@Id`), `comment`, `completion_status` (omit → `null`, kein `Undefined`), `last_modified` (omit → `null`), `default_line` (Suffix von `@DefaultLine`, omit → `null`). Dict-Key bleibt Name.
- Function: `ets_id` (= `identifier` `F-n`), `description`, `comment`, `completion_status`, `last_modified` (leer/omit → `null`).

Nächste additive Extras (optionaler Key, Default-Struktur bleibt):

- `ets_id` (`DI-n`, `GA-n`, `GR-n`) an den restlichen Objekten bzw. Extra-Map
- `XMLGroupRange` hat heute **kein** `Id` — erste echte Parser-Lücke
- Topology: Segmente als eigene Objekte (heute oft nur erstes Segment für MediumType)
- Device: `LastDownload` (Sentinel `0001-01-01` nicht als echt behandeln), `*Loaded`, Serial Base64→Hex-Hinweis, ChannelInstance vs. GroupObjectTree, Folders `PB-*`, COs **ohne** GA-Links
- Trades + DeviceInstanceRef
- knx_master-Katalog: Top-Level-Key `master_data` nur bei `parse(combine=False)` (Entities + alle Languages außer en-US). Default/HA (`combine=True`) parst nicht alle Languages und hat den Key nicht. Keine zweite `parse()`-Methode.

## `combine`

`combine_project` inferiert fehlende DPT aus KO-Größe. Das ist HA-Default. KSS will das **nicht**. Deshalb `parse(combine=False)` in `kss/services/knxproj.py`.

## Tests im Fork

Bestehende Stubs unter `test/resources/stubs/` müssen mit Default-`parse()` weiter passen. `assert_stub` erlaubt extra Keys auf `info` sowie auf jedem Space in `locations` (inkl. nested `spaces`) und jedem Function-Objekt in `functions`; Stub-JSON muss diese Extras nicht listen. Top-Level-Keys außer `info` und die Dict-Keys (Location-Name, Function-`F-n`) bleiben exakt.

KSS-Korpus `research/`: alle `*.knxproj` für XSD (WA53H10 produktiv, Guid `666d92fe-6df1-445e-8c0a-a9be732a8c3f`; `test_A*` Reverse Engineering). TTL: alle `*.ttl`, Skill `knx-semantik`. WA53H10 optional Smoke für den Fork.
