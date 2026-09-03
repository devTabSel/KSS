# Export

Rekonstruktion aus der versionierten DB. Originaldateien werden nicht gespeichert. Kein Passwort; knxproj-ZIP unverschlüsselt.

HTTP: `GET /api/kss/installations/{id}` in `src/kss/api/installations.py`. Snapshot: `kss.services.snapshot.snapshot_installation`. Serializer: `kss.services.ttl_export.serialize_ttl`, `kss.services.knxproj_export.serialize_knxproj` (KSS-Writer, kein xknxproject-Dump). Tests: `tests/test_export.py`, `tests/test_export_roundtrip.py`.

Ingest: [ingest.md](ingest.md). Lookup: [temporal.md](temporal.md).

## Negotiation

Query `format` überschreibt Accept. Token (führender Punkt egal): `ttl`/`turtle` → Turtle; `knxproj`/`zip` → knxproj. Unbekannt → **422**.

Accept (erster Range, ohne q): `text/turtle` / `text/ttl`; `application/vnd.knx.knxproj+zip` / `application/zip` / `application/x-knxproj`.

`at` ISO-8601; weglassen = aktuell. Ungültig → **422**. Keine Version `<= at` → **404**.

`less_info` Default **true**, nur knxproj. Inverse von PATCH `parse(..., more_info=True, include_catalog=True)`. `less_info=false` schreibt Extra-Felder (Trades, Loaded-Flags, BCUKey, …).

`/api/v1` + Datei-Accept/`format` → **406** (`file export is only available under /api/kss`).

Antwort: Rohkörper, `Content-Disposition: attachment; filename="{title}.ttl|.knxproj"`.

JSON ohne Datei-Negotiation: `get_at` (Flavor `kss` wertet `at` aus; `/api/v1` ignoriert `at`).

## Snapshot

`snapshot_installation(session, id, at)` lädt alle Pakete zu `t` über `version_at` / `E(entity, t)`: Locations, Functions, Topology, Devices, Parts, Datapoints, GroupRanges, Trades, verknüpfte Kanten (`linked=true`). Keine Installations-Version `<= t` → `None` (HTTP 404).

`contributions`: knxproj-Trades → TTL (`prj:T-*` als NamedIndividual, `dct:title`, description/comment/number/state, `core:lastModified`, Parent `knx:hasTrade`, `knx:hasDevice`); `mac:assignedTrade` am Device, wenn die Device-Version keinen TTL-Namen hat. Tag-Store-Hook leer.

## Turtle

Canonical Turtle: deterministische Prefixes/Subjects/Predicates; `rdf:type` als `a`; Datetimes `Z`. `parse_ttl` verlangt Instanzblock ab `prj:`.

KSS-TTL enthält `prj:T-*`. Roundtrip-Akzeptanz: Export → leere DB → Import → Export identisch.

## knxproj

Unverschlüsseltes ZIP (`{P-id}.signature`, `knx_master.xml`, `{P-id}/project.xml`, `{P-id}/0.xml`). Schema aus `schema_version` oder 23. Segment `MediumTypeRefId` = Segment-Medium, sonst Line-Medium (ETS-6 liest das erste Segment).
