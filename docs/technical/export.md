# Export

Rekonstruktion aus der versionierten DB. Originaldateien werden nicht gespeichert. Kein Passwort; knxproj-ZIP unverschlüsselt.

HTTP: `GET /api/kss/installations/{id}` (aktuell) oder `GET /api/kss/{t}/installations/{id}` in `src/kss/api/installations.py`. Snapshot: `kss.services.snapshot.snapshot_installation`. Serializer: `kss.services.ttl_export.serialize_ttl`, `kss.services.knxproj_export.serialize_knxproj` (KSS-Writer, kein xknxproject-Dump). Tests: `tests/test_export.py`, `tests/test_export_roundtrip.py`.

Ingest: [ingest.md](ingest.md). Lookup: [temporal.md](temporal.md).

## Negotiation

Query `format` überschreibt Accept. Token (führender Punkt egal): `ttl`/`turtle` → Turtle; `knxproj`/`zip` → knxproj. Unbekannt → **422**.

Accept (erster Range, ohne q): `text/turtle` / `text/ttl`; `application/vnd.knx.knxproj+zip` / `application/zip` / `application/x-knxproj`.

`{t}` ISO-8601 im Pfad (`:` percent-encoded). Ungültig → **422**. Query `?at=` entfällt.

`less_info` Default **true**, nur knxproj. Inverse von PATCH `parse(..., more_info=True, include_catalog=True)`. `less_info=false` schreibt Extra-Felder (Trades, Loaded-Flags, BCUKey, …).

`/api/v1` + Datei-Accept/`format` → **406** (`file export is only available under /api/kss`).

Antwort: Rohkörper, `Content-Disposition: attachment; filename="{title}.ttl|.knxproj"`. GET `/api/kss` setzt Header `resolution`.

## Snapshot

`snapshot_installation(session, id, at)` lädt jedes Paket mit demselben HTTP-Lookup (`take_version` / `resolve_version`): Locations, Functions, Topology, Devices, Parts, Datapoints, GroupRanges, Trades, verknüpfte Kanten (`linked=true`). Request-Header `resolution` Default `assumed`: fehlt `E(entity, t)`, erste Version nach `t`. `resolution: exact` lässt solche Objekte weg. Ein angenommenes Paket oder eine angenommene Kante setzt Response-Header `resolution: assumed`. Keine Installations-Version unter der Policy → `None` (HTTP 404). Ohne `{t}` (`at is None`) bleibt der Export aktuell (`max(last_modified)`, nie assumed).

`contributions`: knxproj-Trades → TTL (`prj:T-*` als NamedIndividual, `dct:title`, description/comment/number/state, `core:lastModified`, Parent `knx:hasTrade`, `knx:hasDevice`); `mac:assignedTrade` am Device, wenn die Device-Version keinen TTL-Namen hat. Tag-Store-Hook leer.

## Turtle

Canonical Turtle: deterministische Prefixes/Subjects/Predicates; `rdf:type` als `a`; Datetimes `Z`. `parse_ttl` verlangt Instanzblock ab `prj:`.

KSS-TTL enthält `prj:T-*`. Roundtrip-Akzeptanz: Export → leere DB → Import → Export identisch.

## knxproj

Unverschlüsseltes ZIP (`{P-id}.signature`, `knx_master.xml`, `{P-id}/project.xml`, `{P-id}/0.xml`, `M-*/Hardware.xml`, `M-*/{A-Id}.xml`). Schema aus `schema_version` oder 23. Segment `MediumTypeRefId` = Segment-Medium, sonst Line-Medium (ETS-6 liest das erste Segment).

`knx_master.xml` Manufacturers aus `master_manufacturers`. `0.xml` DeviceInstance: `ProductRefId` = `product_ref`, `Hardware2ProgramRefId` = `hardware_program_ref`. Hersteller-XML aus dem globalen Katalog, nicht als Original-Blob.
