# Location (inkl. Function)

3API `location` + ETS Space + **ApplicationFunction**. Function ist kein eigenes Paket.

Archiviert nach `docs/evolving/` am 2026-09-02 (reDoc). Nicht verbindlich.

## Location

- Identität: `installation_id`, `ets_id` (`BP-n`), `puid`.
- Version: 3API title/description/comment/`@type`; `location_type` = XSD `SpaceType_t` (nicht knx_master); `usage` = `SU-*` oder `tag:bedroom`; `number`; `completion_status`; `parent_location_id` (nicht self); `default_line_id` → `lines.id`.
- Synthetisches `loc:Site`: optional, Dummy-Titel/`42`/`Unknown` nicht als echte Daten.

## Function

TTL `core:ApplicationFunction`, Join `F-n`. `core:Functionality` (UUID-Beutel) nicht persistieren.

- Version: 3API-Felder + `function_type_ets_id` (`FT-*`, oft `FT-0`) + `location_id` FK.
- `function_datapoints` temporal: `role` (`GroupAddressRef/@Role`, `DR-*` oder UUID), `ets_id` `GF-*`, `linked`.
