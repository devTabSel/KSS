# Stand (Ist)

Stand der Live-Doku: 2026-09-03, nach `/api/kss/{t}/` Lookup.

## Umgesetzt

- Persistenz der Pakete Installation, Location (inkl. Function), Topology, Device, Datapoint, Trade
- temporale Versionen über `last_modified`; Import-Uhr `last_import`; Lookup Stand zu `t`
- BUS-Indizes `bus_pa_bindings` / `bus_ga_bindings` im Schema; knxproj-PATCH befüllt sie (kein GET)
- GET Collection/Item: Installation, Location, Function, Device, Datapoint auf `/api/v1` und `/api/kss`
- GET nur `/api/kss`: Topology (Area/Line/Segment), Trade, GroupRange, Channel, Folder, CommObject
- PATCH `.knxproj` und `.ttl` unter `/api/kss/installations` (201 neu / 204 Reimport); knxproj über den Fork ohne DPT-Inferenz, mit Extra-Keys, knx_master-Katalog und globalem Hersteller-XML-Katalog
- TTL persistiert `prj:T-*` und `knx:hasDevice` (KSS-Turtle roundtrippt). ETS Semantic Export hat typischerweise keine `prj:T-*` → 0 Gewerke
- Device: 3API `orderNumber`/`manufacturer` aus dem Produktkatalog (Join; weglassen wenn Produkt fehlt). Unter `/api/kss` zusätzlich `kss:assignedTrade`, `kss:operatesForTrade` (nicht leer), `kss:hardwareProgramRef`
- Datei-Export unter `/api/kss`: `GET /api/kss/installations/{id}` als `.ttl` / `.knxproj` zum Stand `t` (Rekonstruktion aus Katalog + versionierter DB, keine Originaldatei)
- JSON-GET und Datei-Export zum Stand `t` unter `/api/kss/{t}/…` (Request-Header `resolution` Default `assumed`, sonst `exact`); `/api/v1` immer aktuell

## Bewusst noch nicht

- JSON-LD-Ingest
- TTL erzeugt keine Topologie `A-*`/`L-*`/`S-*`, keine Kanäle/Ordner/COs, keine BUS-Indizes, keine GroupRanges, kein `prj:Site` (das macht knxproj)
- kein automatisches Verknüpfen des TTL-Gewerkenamens (`mac:assignedTrade`) mit den Gewerken `T-n`
- Tag-Store / reiche `@type`-Synthese über die bereits gespeicherten `rdf:type`-CURIEs hinaus
- OAuth / `/.well-known/knx`
- Runtime-Werte / Telegramm-API
- GET-Soll (eingebettete Ressourcen, Filter, Node) — Ist bleibt Identifier

Was fehlt, ist Absicht oder nächster Ausbauschritt — nicht ein versteckter zweiter Server.
