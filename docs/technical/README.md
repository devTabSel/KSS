# KSS — technische Dokumentation

Für **Weiterentwicklung**. Nutzer-Sicht: [`docs/fachlich/`](../fachlich/README.md). Archiv: [`docs/evolving/`](../evolving/README.md) — nicht verbindlich.

KSS ist die temporale Semantikquelle: Ingest aus `.knxproj` und `.ttl`, zwei HTTP-Verträge, Clients lesen statt selbst zu parsen. Archivierte Zielpläne (nicht verbindlich): [`docs/evolving/2026-09-04-cursor-os/plans/README.md`](../evolving/2026-09-04-cursor-os/plans/README.md).

## Layout

| Thema | Datei |
| --- | --- |
| Persistenz, Pakete, Alembic | [persistenz.md](persistenz.md) |
| Temporal / BUS | [temporal.md](temporal.md) |
| HTTP-Src und Flavors | [http.md](http.md) |
| PATCH-Ingest, Fork-`parse` | [ingest.md](ingest.md) |
| GET Datei-Export (Stand zu `t`) | [export.md](export.md) |
| Paket-Mappings | [models/](models/README.md) |

Arbeit auf `main`, sofern kein Branch verlangt ist.
