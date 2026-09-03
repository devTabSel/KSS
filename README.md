# KSS

KNX Semantic Server: temporale Semantikquelle für ETS-Installationen.

- **Fachlich** (Nutzer, Clients): [`docs/fachlich/README.md`](docs/fachlich/README.md)
- **Technisch** (Weiterentwicklung): [`docs/technical/README.md`](docs/technical/README.md)
- **Archiv / Notizen** (nicht verbindlich): [`docs/evolving/README.md`](docs/evolving/README.md)

Ingest: `PATCH /api/kss/installations` (`.knxproj` oder `.ttl`). Lesen: `/api/v1` (3API) und `/api/kss` (plus `kss:`).
