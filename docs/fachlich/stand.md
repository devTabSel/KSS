# Stand (Ist)

Stand der Live-Doku: 2026-09-02, nach erstem KSS-reDoc.

## Umgesetzt

- Persistenz der Pakete Installation, Location (inkl. Function), Topology, Device, Datapoint, Trade
- temporale Versionen über `last_modified`; Import-Uhr `last_import`
- BUS-Tabellen `bus_pa_bindings` / `bus_ga_bindings` im Schema
- HTTP: GET Installation auf `/api/v1` und `/api/kss`
- PATCH `.knxproj` → Installation (Mapper aus Parser-`info`)

## Bewusst noch nicht

- TTL-/JSON-LD-Ingest (501)
- GET/PATCH für Location, Topology, Device, Datapoint, Trade
- OAuth
- Telegramm-API
- Home Assistant liest KSS (Richtungsplan, nicht jetzt)

Was fehlt, ist Absicht oder nächster Ausbauschritt — nicht ein versteckter zweiter Server.
