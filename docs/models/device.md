# Device

3API `device` plus Download-/Produkt-/Kanalstruktur. `assigned_trade` gibt es nicht (siehe Trade).

## Device

Identität: `installation_id`, `ets_id` (`DI-n`), `puid`.

Version (Kat. 1 plus 3): title (XML `@Name` oder Produkt), description, comment, order_number, manufacturer, last_modified, last_downloaded (kein Sentinel `0001-01-01`), current_date_time, serial_number (eine Hex-Spalte), individual_address (3API-Punktnotation), firmware/hardware, `@type`, `location_id` FK, `segment_id` FK, `completion_status`, `communication_part_loaded`, `product_ref`, `application_program_ref`, `bus_current`, `installation_hints`.

`_since`: echtes `LastDownload`, sonst `LastModified`. `CommunicationPartLoaded=true` allein reicht nicht.

## Unterobjekte

- `device_channels`: kanonisch `ChannelInstance/@Id`; `catalog_ref` = `@RefId`. Ohne ChannelInstances ist TTL `CI-n` nicht Baumordnung.
- `device_folders`: `PB-*`, knxproj-only.
- `comm_objects`: `O-…_R-…` = TTL `core:Datapoint` (nicht die GA).
- `comm_object_datapoints`: N:M temporal, `linked`.

Bus veraltet, wenn `communication_part_loaded` false oder `last_downloaded` < `_since` der GA-/Link-Änderung (abgeleitet, keine Extra-Spalte).
