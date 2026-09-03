# Temporal und BUS

Kanonisch: `src/kss/models/temporal.py`, `src/kss/services/temporal.py` (`version_at`) und `.cursor/plans/temporal-bus-semantics.md`.

## ETS-Version

`last_modified` (NOT NULL, PK-Teil) ist der einzige ETS-Versionsschlüssel und 3API `lastModified`, wo zutreffend.

- Wert: Objekt-`LastModified`, sonst `ProjectInformation/@LastModified`.
- Neue Version nur bei semantischem Diff.
- Gleiches `(entity_id, last_modified)` → keine zweite Zeile.
- Historische Zeilen werden nicht aktualisiert.
- GET-aktuell = `max(last_modified)`.
- Lookup `E(entity, t)` = Zeile mit `max(last_modified) <= t`. Keine Zeile → kein Stand (HTTP 404).
- `t is None` → aktuell. Implementierung: `version_at`.

HTTP: JSON-GET `/api/kss/installations/{id}?at=` nutzt `get_at` (Installations-Version zu `t`). `/api/v1` ignoriert `at` (immer aktuell). Ungültiges `at` → 422. Datei-Export lädt **alle** Pakete zu demselben `t` (`snapshot_installation` in `kss.services.snapshot`, Kanten mit `linked=true`). Details: [export.md](export.md).

## Import-Uhr

`installations.last_import` (UTC) bei jedem PATCH-Ingest. Nicht Teil der Versions-PK. JSON:API: `kss:lastImport` (nur Flavor `kss`).

## BUS

Materialisiert in `bus_pa_bindings` und `bus_ga_bindings`. Device-Flags `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded`.

Wirksam frühestens ab `last_downloaded`, wenn die jeweiligen `*Loaded`-Flags true sind. PA- und GA-Bindings können zu unterschiedlichen `last_downloaded` springen.

Telegramm zur Zeit `t`: BUS-Indizes, dann ETS-Lookup `E(entity, t)`. Device-Import befüllt die Indizes; Telegramm-HTTP ist offen.
