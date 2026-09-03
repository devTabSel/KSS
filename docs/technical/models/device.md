# Device

3API `device` plus Download-/Produkt-/Kanalstruktur. `assigned_trade` / `operates_for_trade` liegen auf `device_versions` (kein FK auf `trades`). knxproj-PATCH befüllt `bus_pa_bindings`/`bus_ga_bindings`; kein Collection-GET für die Indizes. GET Device auf `/api/v1` und `/api/kss`.

## Device

Identität: `installation_id`, `ets_id` (`DI-n`).

Version (Kat. 1 plus 3): title (XML `@Name` oder Produkt), description, comment, order_number, manufacturer, `last_modified` (PK-Teil), `last_downloaded` (timestamptz nullable; Sentinel `0001-01-01` nicht speichern — Importer), serial_number (roh Base64 wie knxproj/xknxproject `@SerialNumber`, z. B. WA53H10 `AKYmAAR/`; Omit/leer → NULL), individual_address, firmware/hardware, `@type`, `location_id` FK, `segment_id` FK, `completion_status`, `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded` (Boolean NOT NULL default false; Upstream-Omit → false), `product_ref`, `application_program_ref`, `bus_current`, `installation_hints`, `assigned_trade`, `operates_for_trade`.

TTL (`core:Device` only): `assigned_trade` ← `mac:assignedTrade` (Name, nicht `T-n`); `operates_for_trade` ← `tag:operatesForTrade`; IA Hex→dotted; Serial `$hex` (`$00A62600047F`) → dieselbe Base64; Sentinel `0001-01-01` `lastDownloaded` nicht gespeichert (Importer). knxproj schreibt `assigned_trade` nicht; Preserve der Loaded-Flags und `segment_id` beim TTL-Join. Fork `last_download`/`*Loaded` wie XKNX; Sentinel-Drop nur Importer.

GET `/api/kss`: `kss:assignedTrade` wenn gesetzt, `kss:operatesForTrade` wenn nicht leer. Weder unter `/api/v1` noch als 3API `assignedTrade`.

ETS versioniert mit `last_modified`. BUS-Bindings in `bus_pa_bindings` / `bus_ga_bindings`. GET-aktuell = `max(last_modified)`. Telegramm/Bus: Indizes nach `last_downloaded`; ETS-Semantik via `E(entity, t)`.

## Unterobjekte

- `device_channels`: kanonisch `ChannelInstance/@Id`; `catalog_ref` = `@RefId`. Ohne ChannelInstances ist TTL `CI-n` nicht Baumordnung. TTL persistiert keine Channels.
- `device_folders`: `PB-*`, knxproj-only.
- `comm_objects`: `O-…_R-…` = TTL `core:Datapoint` (nicht die GA). TTL persistiert COs nicht als Datapoints.
- `comm_object_datapoints`: N:M temporal, `linked`.
