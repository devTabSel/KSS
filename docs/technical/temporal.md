# Temporal und BUS

Kanonisch: `src/kss/models/temporal.py` und `.cursor/plans/temporal-bus-semantics.md`.

## ETS-Version

`last_modified` (NOT NULL, PK-Teil) ist der einzige ETS-Versionsschlüssel und 3API `lastModified`, wo zutreffend.

- Wert: Objekt-`LastModified`, sonst `ProjectInformation/@LastModified`.
- Neue Version nur bei semantischem Diff.
- Gleiches `(entity_id, last_modified)` → keine zweite Zeile.
- Historische Zeilen werden nicht aktualisiert.
- GET-aktuell = `max(last_modified)`.
- Lookup `E(entity, t)` = Zeile mit `max(last_modified) <= t`.

## Import-Uhr

`installations.last_import` (UTC) bei jedem PATCH-Ingest. Nicht Teil der Versions-PK. JSON:API: `kss:lastImport` (nur Flavor `kss`).

## BUS

Materialisiert in `bus_pa_bindings` und `bus_ga_bindings`. Device-Flags `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded`.

Wirksam frühestens ab `last_downloaded`, wenn die jeweiligen `*Loaded`-Flags true sind. PA- und GA-Bindings können zu unterschiedlichen `last_downloaded` springen.

Telegramm zur Zeit `t`: BUS-Indizes, dann ETS-Lookup `E(entity, t)`. Device-Importer und Telegramm-HTTP sind offen; das Schema liegt.
