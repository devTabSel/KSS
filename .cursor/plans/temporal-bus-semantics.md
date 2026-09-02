# Temporale Semantik: ETS-Versionen und BUS-Indizes

Verbindlich für Modellierer, APIler und Importer. Einordnung: [README](README.md).

Großes Ziel: Telegramme und Clients sehen denselben zeitlichen Stand — ETS-Projektstand und bus-wirksamen Download-Stand getrennt, nicht vermischt.

## Schichten

| Schicht | Inhalt |
| --- | --- |
| ETS | `*_versions` mit PK `(entity_id, last_modified NOT NULL)` |
| Import-Uhr | `installations.last_import` (UTC, bei jedem PATCH-Ingest) |
| BUS | `bus_pa_bindings`, `bus_ga_bindings` (materialisiert beim Device-Import) |

## Erkenntnisse A–E

| ID | Regel |
| --- | --- |
| A | Neue Version nur bei semantischem Diff; `last_modified` aus ETS, nicht Import-Uhr |
| B | BUS frühestens ab `last_downloaded`, wenn jeweiliges `*Loaded=true` |
| C | Telegramme nutzen BUS-Indizes, dann ETS-`E(...)` |
| D | ETS in Versionstabellen; BUS nur in Indizes + Device-Flags/`last_downloaded` |
| E | PA- und GA-Bindings können zu unterschiedlichen `last_downloaded` springen |

## ETS-Versionierung

- **`last_modified`** ist PK-Teil und 3API `lastModified` (eine Spalte).
- Wert beim Import: Objekt-`LastModified`, sonst `ProjectInformation/@LastModified`.
- Kein `INITIAL_SINCE`, keine Extra-Zeile `_since = LastDownload`.
- Lookup: `E(entity, t) =` Zeile mit `max(last_modified) <= t`.
- Aktuell: `max(last_modified)`.
- Gleiches `(entity_id, last_modified)`: keine zweite Zeile.

## Import-Uhr

- **`installations.last_import`**: UTC-Zeitpunkt des letzten erfolgreichen PATCH-Ingest.
- Ersetzt `_observable_since` auf Versionen.
- JSON:API `/api/kss`: Attribut `kss:lastImport`.

## BUS-Indizes

### `bus_pa_bindings`

PK: `(installation_id, individual_address, last_downloaded)` → `device_id`

Befüllung: nur wenn `individual_address_loaded=true` und echtes `LastDownload` (Sentinel `0001-01-01` nie speichern).

### `bus_ga_bindings`

PK: `(installation_id, group_address, device_id, last_downloaded)`

Befüllung: Device mit `communication_part_loaded=true` und echtem `LastDownload`; verknüpfte KOs mit `linked=true`.

### Device `*Loaded`-Flags

`communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded` steuern, welche BUS-Zeilen geschrieben werden.

## Lookup BUS

- **PA:** `max(last_downloaded) <= t` für `(installation_id, individual_address)`.
- **GA:** Zeilen mit `group_address = g` und `max(last_downloaded) <= t` pro `(installation_id, device_id)`.

## Stand / danach

Umgesetzt: Mixin `TemporalVersionMixin`, Migration `003_temporal_lm_bus`, Installation-PATCH setzt `last_import`.

Offen (Importer / später APIler): Device-Import befüllt Indizes; `telegram_semantics.py` (`resolve_source_pa`, `resolve_target_ga`, `confidence`); weitere BUS-Teile (App/Params/Medium) als Indizes.

Verwandt: [PATCH Installation exports](patch-installation-exports.md), [KSS and KNX 3rd Party API](kss-and-knx-3rd-party-api.md), [HomeAssistant KNX Integration](homeassistant-knx-integration.md).
