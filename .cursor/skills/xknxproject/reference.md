# xknxproject — Lücken und nächste Keys

Parser-Output ist ein `KNXProject`-Dict. KSS mappt ihn; dieser Skill ändert nur den Fork.

## Interne Ids vs. Dict-Keys

Der Fork kennt knxproj-`@Id` intern (`DeviceInstance.identifier`, `XMLSpace.identifier`, `XMLGroupAddress.identifier`). `_transform()` wirft sie für Locations/Ranges oft weg. Dict-Keys sind heute IA bzw. Name — für KSS unbrauchbar als Identität.

Nächste additive Extras (optionaler Key, Default-Struktur bleibt):

- `ets_id` (`DI-n`, `BP-n`, `GA-n`, `GR-n`) an den Objekten bzw. Extra-Map
- `XMLGroupRange` hat heute **kein** `Id` — erste echte Parser-Lücke
- Topology: Segmente als eigene Objekte (heute oft nur erstes Segment für MediumType)
- Device: `LastDownload` (Sentinel `0001-01-01` nicht als echt behandeln), `*Loaded`, Serial Base64→Hex-Hinweis, ChannelInstance vs. GroupObjectTree, Folders `PB-*`, COs **ohne** GA-Links
- Trades + DeviceInstanceRef
- knx_master-Katalog nur soweit billig; teure Indizes als weitere optionale Keys, nicht als zweite `parse()`-Methode

## `combine`

`combine_project` inferiert fehlende DPT aus KO-Größe. Das ist HA-Default. KSS will das **nicht**. Deshalb `parse(combine=False)` in `kss/services/knxproj.py`.

## Tests im Fork

Bestehende Stubs unter `test/resources/stubs/` müssen mit Default-`parse()` weiter passen. Neue Keys in Stubs nachziehen, wenn TypedDict sie Pflicht macht. `assert` in Tests darf extra `info`-Keys erlauben.

KSS-Korpus `research/`: alle `*.knxproj` für XSD (WA53H10 produktiv, Guid `666d92fe-6df1-445e-8c0a-a9be732a8c3f`; `test_A*` Reverse Engineering). TTL: alle `*.ttl`, Skill `knx-semantik`. WA53H10 optional Smoke für den Fork.
