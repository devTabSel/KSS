# HTTP (Src)

Skill `kss-api` (KSS-API), Plan [KSS and KNX 3rd Party API](../../.cursor/plans/kss-and-knx-3rd-party-api.md). Einstieg: `src/kss/main.py`.

## Prefixes

`/api/v1` und `/api/kss` sind Mount-Prefixes derselben Router, keine Pakete `api/v1/` / `api/kss/`.

```
src/kss/api/
  deps.py            # PageNumber / PageSize; SessionDep
  flavor.py          # bind_flavor, ExtraDep
  jsonapi.py         # Hülle, Serializer extra=
  installations.py   # read_router + kss_router (PATCH)
```

`Flavor = Literal["v1", "kss"]`. `ExtraDep` ist true genau bei Flavor `kss`. URL-Pfad nicht parsen.

`read_router` unter beiden Prefixes; `kss_router` nur unter `/api/kss`. PATCH nicht auf `read_router`.

Pagination-Defaults nur in `deps.py` (`page[number]` 0, `page[size]` 65536).

## Ist

Nur Installation verdrahtet. Weitere Entitäten: eine Datei `kss/api/<entity>.py` analog, nach Freigabe des Modells.

Serializer: Kategorie-1 immer; `kss:`-Keys nur wenn `extra` (inkl. `kss:lastImport`).
