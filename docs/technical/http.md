# HTTP (Src)

Skill `kss-api` (KSS-API), Plan [KSS and KNX 3rd Party API](../../.cursor/plans/kss-and-knx-3rd-party-api.md). Einstieg: `src/kss/main.py`.

## Prefixes

`/api/v1` und `/api/kss` sind Mount-Prefixes derselben Router, keine Pakete `api/v1/` / `api/kss/`.

```
src/kss/api/
  deps.py            # PageNumber / PageSize; SessionDep
  flavor.py          # bind_flavor, ExtraDep
  jsonapi.py         # Hülle, Serializer extra=
  installations.py   # GET both (JSON; kss: ?at= + Datei-Export); PATCH kss (.knxproj / .ttl)
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

`Flavor = Literal["v1", "kss"]`. `ExtraDep` ist true genau bei Flavor `kss`. URL-Pfad nicht parsen.

`read_router` unter beiden Prefixes; `kss_router` nur unter `/api/kss`. PATCH nicht auf `read_router`. Extra-Verben (PATCH-Ingest, Datei-GET) nur `/api/kss`.

Pagination-Defaults nur in `deps.py` (`page[number]` 0, `page[size]` 65536).

## Ist

GET Collection/Item für die verdrahteten Entitäten. Relationships sind Resource Identifier (`data: {type, id}`), kein `links.related`, kein Nested, kein Filter, kein Node. `@type` in `meta.@type` aus gespeicherten `rdf:type`-CURIEs.

Serializer: Kategorie-1 immer; `kss:`-Keys nur wenn `extra` (inkl. `kss:lastImport`). Device: `kss:assignedTrade` wenn gesetzt, `kss:operatesForTrade` wenn nicht leer — nur Flavor `kss`, nicht 3API `assignedTrade`.

### GET Item Installation

`GET …/installations/{id}` in `installations.py`. Query `at`, `format`, `less_info`. `format` überschreibt Accept.

- JSON (kein Datei-`format`/Accept): Flavor `kss` → `get_at` mit `at`; Flavor `v1` ignoriert `at` (aktuell).
- Datei: nur Flavor `kss` → Snapshot + `serialize_ttl` / `serialize_knxproj`. Flavor `v1` → **406**.
- Ungültiges `format`/`at` → **422**. Keine Version `<= at` → **404**.

`less_info` Default true, nur knxproj. PATCH bleibt Ingest (Collection). Details: [export.md](export.md), [ingest.md](ingest.md).
