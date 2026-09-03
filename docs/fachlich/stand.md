# Stand (Ist)

Stand der Live-Doku: 2026-09-03, nach TTL Semantic Export ingest.

## Umgesetzt

- Persistenz der Pakete Installation, Location (inkl. Function), Topology, Device, Datapoint, Trade
- temporale Versionen über `last_modified`; Import-Uhr `last_import`
- BUS-Indizes `bus_pa_bindings` / `bus_ga_bindings` im Schema; knxproj-PATCH befüllt sie (kein GET)
- GET Collection/Item: Installation, Location, Function, Device, Datapoint auf `/api/v1` und `/api/kss`
- GET nur `/api/kss`: Topology (Area/Line/Segment), Trade, GroupRange, Channel, Folder, CommObject
- PATCH `.knxproj` und `.ttl` unter `/api/kss/installations` (201 neu / 204 Reimport)
- Device unter `/api/kss`: `kss:assignedTrade`, `kss:operatesForTrade` (nicht leer)

## Bewusst noch nicht

- JSON-LD-Ingest
- TTL erzeugt keine Topologie, keine Gewerke `T-n`, keine Kanäle/Ordner/COs, keine BUS-Indizes, keine GroupRanges (das macht knxproj)
- kein automatisches Verknüpfen des TTL-Gewerkenamens mit den knxproj-Gewerken
- Tag-Store / reiche `@type`-Synthese über die bereits gespeicherten `rdf:type`-CURIEs hinaus
- OAuth / `/.well-known/knx`
- Runtime-Werte / Telegramm-API
- GET-Soll (eingebettete Ressourcen, Filter, Node) — Ist bleibt Identifier

Was fehlt, ist Absicht oder nächster Ausbauschritt — nicht ein versteckter zweiter Server.
