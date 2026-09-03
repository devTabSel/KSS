# HTTP (Src)

Skill `kss-api` (KSS-API), Plan [KSS and KNX 3rd Party API](../../.cursor/plans/kss-and-knx-3rd-party-api.md). Einstieg: `src/kss/main.py`.

## Prefixes

`/api/v1` und `/api/kss` sind Mount-Prefixes derselben Router, keine Pakete `api/v1/` / `api/kss/`.

```
src/kss/api/
  deps.py            # PageNumber / PageSize; SessionDep
  flavor.py          # bind_flavor, ExtraDep, /api/kss/{at}
  jsonapi.py         # Hülle, Serializer extra=
  installations.py   # GET both (JSON + Datei-Export unter kss); PATCH kss (.knxproj / .ttl)
  locations.py       # GET both
  functions.py       # GET both
  devices.py         # GET both
  datapoints.py      # GET both; kss_router group-ranges
  topology.py        # GET kss: areas / lines / segments
  trades.py          # GET kss
  channels.py        # GET kss
  folders.py         # GET kss
  comm_objects.py    # GET kss
```

`Flavor = Literal["v1", "kss"]`. `ExtraDep` ist true genau bei Flavor `kss`. Zeitreise: `GET /api/kss/{at}/…` (`at` ISO-8601); Query `?at=` entfällt.

`read_router` unter `/api/v1`, `/api/kss` und `/api/kss/{at}`; `kss_router` (PATCH) nur unter `/api/kss`. PATCH nicht auf `read_router`. Extra-Verben (PATCH-Ingest, Datei-GET) nur `/api/kss`.

Pagination-Defaults nur in `deps.py` (`page[number]` 0, `page[size]` 65536).

## Ist

GET Collection/Item für die verdrahteten Entitäten. Relationships sind Resource Identifier (`data: {type, id}`), kein `links.related`, kein Nested, kein Filter, kein Node. `@type` in `meta.@type` aus gespeicherten `rdf:type`-CURIEs.

Serializer: Kategorie-1 immer; `kss:`-Keys nur wenn `extra` (inkl. `kss:lastImport`). Device: 3API `orderNumber`/`manufacturer` per Join `MasterProduct` (weglassen wenn `product_ref` oder Katalogzeile fehlt); Flavor `kss`: `kss:assignedTrade` wenn gesetzt, `kss:operatesForTrade` wenn nicht leer, `kss:hardwareProgramRef` wenn gesetzt — nicht 3API `assignedTrade`.

### GET Item Installation

`GET …/installations/{id}` in `installations.py`. Query `format`, `less_info`. `format` überschreibt Accept. Zeitpunkt nur als Pfad `/api/kss/{at}/installations/{id}`.

- JSON: `/api/v1` und `/api/kss` aktuell (`max(last_modified)`). `/api/kss/{at}` Stand `t` (`resolve_version`); Request-Header `resolution` Default `assumed`, sonst `exact`.
- Datei: nur Flavor `kss` → Snapshot + `serialize_ttl` / `serialize_knxproj`. Dieselbe `resolution`-Policy wie JSON. Flavor `v1` → **406**.
- Ungültiges `format`/`{at}`/`resolution` → **422**. GET `/api/kss` setzt Response-Header `resolution` (`exact`/`assumed`).

`less_info` Default true, nur knxproj. PATCH bleibt Ingest (Collection). Details: [export.md](export.md), [ingest.md](ingest.md).
