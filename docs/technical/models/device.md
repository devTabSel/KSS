# Device

3API `device` plus Download-/Produkt-/Kanalstruktur. `assigned_trade` gibt es nicht (siehe Trade). knxproj-PATCH befüllt `bus_pa_bindings`/`bus_ga_bindings`; kein Collection-GET für die Indizes.

## Device

Identität: `installation_id`, `ets_id` (`DI-n`), `puid`.

Version (Kat. 1 plus 3): title (XML `@Name` oder Produkt), description, comment, order_number, manufacturer, `last_modified` (PK-Teil), `last_downloaded`, `current_date_time`, serial_number (eine Hex-Spalte), individual_address, firmware/hardware, `@type`, `location_id` FK, `segment_id` FK, `completion_status`, `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded`, `product_ref`, `application_program_ref`, `bus_current`, `installation_hints`.

ETS versioniert mit `last_modified`. BUS-Bindings in `bus_pa_bindings` / `bus_ga_bindings`. GET-aktuell = `max(last_modified)`. Telegramm/Bus: Indizes nach `last_downloaded`; ETS-Semantik via `E(entity, t)`.

## Unterobjekte

- `device_channels`: kanonisch `ChannelInstance/@Id`; `catalog_ref` = `@RefId`. Ohne ChannelInstances ist TTL `CI-n` nicht Baumordnung.
- `device_folders`: `PB-*`, knxproj-only.
- `comm_objects`: `O-…_R-…` = TTL `core:Datapoint` (nicht die GA).
- `comm_object_datapoints`: N:M temporal, `linked`.
