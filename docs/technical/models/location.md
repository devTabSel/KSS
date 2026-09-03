# Location (inkl. Function)

3API `location` + ETS Space + **ApplicationFunction**. Function ist kein eigenes Paket. GET Collection/Item auf `/api/v1` und `/api/kss`. TTL persistiert Spaces und Functions (ohne `prj:Site`); knxproj liefert zusätzlich `default_line_id` und FunctionTypes `FT-*`.

## Location

- Identität: `installation_id`, `ets_id` (`BP-n`), `puid`.
- Version: 3API title/description/comment/`@type`; `location_type` = XSD `SpaceType_t` (nicht knx_master); `usage` = `SU-*` oder `tag:bedroom`; `number`; `completion_status`; `parent_location_id` (nicht self); `default_line_id` → `lines.id` (knxproj; TTL preserve).
- Synthetisches `loc:Site`: optional, Dummy-Titel/`42`/`Unknown` nicht als echte Daten. TTL überspringt `prj:Site`.

## Function

TTL `core:ApplicationFunction`, Join `F-n`. `core:Functionality` (UUID-Beutel) nicht persistieren.

- Version: 3API-Felder + `function_type_ets_id` (`FT-*`, TTL-only oft `FT-0` bzw. Preserve) + `location_id` FK.
- `function_datapoints` temporal: knxproj `role` (`GroupAddressRef/@Role`, `DR-*` oder UUID) und `ets_id` `GF-*`; TTL setzt die Kante aus `knx:hasFunctionPoint` (`linked=true`, ohne Role).
