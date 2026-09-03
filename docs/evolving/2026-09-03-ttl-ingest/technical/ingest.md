# Ingest

`PATCH /api/kss/installations` — Collection, multipart. Handler: `src/kss/api/installations.py`. Service: `src/kss/services/installations.py`. Parser-Brücke: `src/kss/services/knxproj.py`.

## Ablauf knxproj

1. Suffix `.knxproj` (sonst 422; `.ttl` → 501).
2. `XKNXProj.parse(combine=False)` im Fork `devTabSel/xknxproject`.
3. Lookup über `project_guid`. Gleiche Identitätszeile für späteres TTL.
4. `upsert` aus `info`: neue Version nur bei semantischem Diff; `last_modified` aus ETS.
5. `last_import` = Import-UTC.
6. 201 neu / 204 sonst, kein Body.

Schema **≥ 23** lehnt KSS ab. Passwort optional.

Installation-`info` (Fork, additiv): bestehende Keys plus `installation_index`, `ets_id`, `completion_status` (XML-Omit → `Undefined`), `comment`, `master_data_version`, `project_number`, `contract_number`, `project_type` (XML-Token). Leer/Omit → `null`. Sprachlabels (`Familienhaus`) nicht erfinden.

## Nicht umschlüsseln

Locations nicht nach Name, Devices nicht nach Individualadresse. Fehlende Parser-Keys: Agent **Representer** (Skill `xknxproject`).

## Verdrahtet / später

Location…Trade und BUS-Indizes (`bus_pa_bindings`/`bus_ga_bindings`) aus dem Parse-Dict (derselbe PATCH). TTL-Join später.
