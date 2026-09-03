# Device

3API `device` plus Download-/Produkt-/Kanalstruktur. `assigned_trade` / `operates_for_trade` liegen auf `device_versions` (kein FK auf `trades`). knxproj-PATCH befüllt `bus_pa_bindings`/`bus_ga_bindings`; kein Collection-GET für die Indizes. GET Device auf `/api/v1` und `/api/kss`.

## Device

Identität: `installation_id`, `ets_id` (`DI-n`).

Version (Kat. 1 plus 3): title (XML `@Name` oder Produkt), description, comment, `last_modified` (PK-Teil), `last_downloaded` (timestamptz nullable; Sentinel `0001-01-01` nicht speichern — Importer), serial_number (roh Base64 wie knxproj/xknxproject `@SerialNumber`, z. B. WA53H10 `AKYmAAR/`; Omit/leer → NULL), individual_address, firmware/hardware, `@type`, `location_id` FK, `segment_id` FK, `completion_status`, `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded` (Boolean NOT NULL default false; Upstream-Omit → false), `product_ref`, `hardware_program_ref` (HP-Id), `application_program_ref` (nur ApplicationProgram `@Id`, `M-*_A-*`), `bus_current`, `installation_hints`, `assigned_trade`, `operates_for_trade`.

`order_number` und `manufacturer` (Display-Name) liegen nicht auf der Version. Globale Zeile `master_products` (`knx_id` = Device `product_ref`). GET 3API `orderNumber` / `manufacturer`: Join über `MasterProduct`. Fehlt `product_ref` oder die Katalogzeile → Attribute weglassen.

TTL (`core:Device` only): `assigned_trade` ← `mac:assignedTrade` (Name, nicht `T-n`); `operates_for_trade` ← `tag:operatesForTrade`; IA Hex→dotted; Serial `$hex` (`$00A62600047F`) → dieselbe Base64; Sentinel `0001-01-01` `lastDownloaded` nicht gespeichert (Importer). Product-Katalog insert-if-missing aus `core:hasProduct` + `core:orderNumber`/`core:manufacturer`; nicht auf DeviceVersion. knxproj schreibt `assigned_trade` nicht; Preserve der Loaded-Flags und `segment_id` beim TTL-Join. Fork `last_download`/`*Loaded` wie XKNX; Sentinel-Drop nur Importer.

GET `/api/kss`: `kss:assignedTrade` wenn gesetzt, `kss:operatesForTrade` wenn nicht leer, `kss:hardwareProgramRef` wenn gesetzt. Weder unter `/api/v1` noch als 3API `assignedTrade`.

ETS versioniert mit `last_modified`. BUS-Bindings in `bus_pa_bindings` / `bus_ga_bindings`. GET-aktuell = `max(last_modified)`. Telegramm/Bus: Indizes nach `last_downloaded`; ETS-Semantik via `E(entity, t)`.

## Hersteller-XML (global)

Current-state, Unique `knx_id`, kein `installation_id`, kein `master_data_id`, nicht temporal. Insert-if-missing. Alembic `011_manufacturer_xml_catalogs`.

| Tabelle | knx_id |
| --- | --- |
| `master_hardware` | Hardware `@Id` (`M-*_H-*`) |
| `master_products` | Product `@Id` = Device `product_ref`; trägt `order_number`, `manufacturer` |
| `master_hardware2programs` | Hardware2Program `@Id` (`…_HP-*`) |
| `master_application_programs` | ApplicationProgram `@Id` (`M-*_A-*`) |
| `master_application_comm_objects` | Suffix `O-n` (Unique mit `application_program_id`); `function_text`, `object_size` |
| `master_application_comm_object_refs` | Suffix `O-n_R-m`; Overrides `function_text` / `object_size` |

Device-Token auf der Version: `product_ref`, `hardware_program_ref` (HP-Id), `application_program_ref` nur A-Id.

## Unterobjekte

- `device_channels`: kanonisch `ChannelInstance/@Id`; `catalog_ref` = `@RefId`. Ohne ChannelInstances ist TTL `CI-n` nicht Baumordnung. TTL persistiert keine Channels.
- `device_folders`: `PB-*`, knxproj-only.
- `comm_objects`: `O-…_R-…` = TTL `core:Datapoint` (nicht die GA). TTL persistiert COs nicht als Datapoints.
- `comm_object_datapoints`: N:M temporal, `linked`.
