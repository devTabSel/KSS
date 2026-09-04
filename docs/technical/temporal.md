# Temporal und BUS

Kanonisch: `src/kss/models/temporal.py`, `src/kss/services/temporal.py` (`version_at`). Archivierter Plan (nicht verbindlich): [temporal-bus-semantics.md](../evolving/2026-09-04-cursor-os/plans/temporal-bus-semantics.md).

## ETS-Version

`last_modified` (NOT NULL, PK-Teil) ist der einzige ETS-Versionsschlüssel und 3API `lastModified`, wo zutreffend.

- Wert: Objekt-`LastModified`, sonst `ProjectInformation/@LastModified`.
- Neue Version nur bei semantischem Diff.
- Gleiches `(entity_id, last_modified)` → keine zweite Zeile.
- Historische Zeilen werden nicht aktualisiert.
- GET-aktuell = `max(last_modified)`.
- Lookup `E(entity, t)` = Zeile mit `max(last_modified) <= t` (`version_at`).
- HTTP GET `/api/kss/{t}/…`: Request-Header `resolution` Default `assumed` — fehlt `E`, Annahme `min(last_modified) > t` (`resolve_version` / `take_version`). `resolution: exact` ohne Annahme. Ungültiger Wert → 422. Collection, Item, Nested, Kanten und Datei-Export dieselbe Policy. Ein angenommenes Objekt setzt Response-Header `resolution: assumed`.
- `t is None` → aktuell.

HTTP: `GET /api/kss/{t}/…` bindet ein `t` für den ganzen Request. Request-Header `resolution` Default `assumed`, sonst `exact`. `/api/v1` und `/api/kss/…` ohne `{t}` immer aktuell. Ungültiges `{t}` oder `resolution` → 422. Datei-Export unter demselben Pfad und derselben Policy. Details: [export.md](export.md).

## Import-Uhr

`installations.last_import` (UTC) bei jedem PATCH-Ingest. Nicht Teil der Versions-PK. JSON:API: `kss:lastImport` (nur Flavor `kss`).

## BUS

Materialisiert in `bus_pa_bindings` und `bus_ga_bindings`. Device-Flags `communication_part_loaded`, `individual_address_loaded`, `application_program_loaded`, `parameters_loaded`, `medium_config_loaded`.

Wirksam frühestens ab `last_downloaded`, wenn die jeweiligen `*Loaded`-Flags true sind. PA- und GA-Bindings können zu unterschiedlichen `last_downloaded` springen.

Telegramm zur Zeit `t`: BUS-Indizes, dann ETS-Lookup `E(entity, t)`. Device-Import befüllt die Indizes; Telegramm-HTTP ist offen.
