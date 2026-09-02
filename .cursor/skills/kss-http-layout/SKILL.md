---
name: kss-http-layout
description: >-
  KSS HTTP src layout: /api/v1 and /api/kss are FastAPI mount prefixes of one
  module per entity (read_router + optional kss_router), not parallel packages
  api/v1/ and api/kss/. Flavor/ExtraDep, pagination defaults only in deps.py.
  Use when adding or changing JSON:API routes, PATCH ingest, ExtraDep, flavor,
  include_router, or when adding a new entity HTTP module. Do not recreate
  src/kss/api/v1 or src/kss/api/kss packages. Do not use for OAuth, 3API schema
  edits, or unsolicited model/Alembic changes.
---

# KSS HTTP layout

URL-Vertrag und `src`-Layout sind zwei Dinge. Agent **fAPIen** führt beides aus. Skill zuerst lesen, bevor REST geschrieben oder das Installation-Paket kopiert wird.

## URL-Vertrag (unverändert)

| Baum | Vertrag |
| --- | --- |
| `/api/v1` | nur spezifizierte 3API. Collection/Item GET. Kein POST/PATCH für Datei-Ingest. JSON:API, `application/vnd.api+json`, nur Kategorie-1-Felder. |
| `/api/kss` | dieselben relativen Pfade, dieselbe JSON:API-Hülle, dieselben 3API-Verben **plus** Attribute mit Präfix `kss:`. Zusätzliche Verben nur hier. |

Pagination: `page[number]` Default 0, `page[size]` Default 65536 — **nur** in `kss/api/deps.py`, nicht in Handler-Signaturen. Collection-`meta.collection` immer. Item: `data.type`, `data.id`, `attributes.title` Pflicht; weitere 3API-Keys nur wenn gesetzt. `relationships` weglassen, solange leer. Aktuell = `max(last_modified)`. Fehlerhülle analog `Errors.json`.

Die zwei Bäume sind **Mount-Prefixes**, keine zweiten Pakete.

## Src-Soll

```
src/kss/api/
  deps.py            # PageNumber / PageSize inkl. Defaults; SessionDep
  flavor.py          # bind_flavor, ExtraDep aus request.state.api_flavor
  jsonapi.py         # Hülle, Serializer mit extra=
  installations.py   # read_router + kss_router (PATCH-Ingest)
  <entity>.py        # später analog, eine Datei je Entität
```

Verboten: `src/kss/api/v1/`, `src/kss/api/kss/`, dünne Zwillinge nur für `extra=True/False`, `*_http.py` nur um zwei Route-Module zu teilen.

### flavor.py

`Flavor = Literal["v1", "kss"]`. `bind_flavor(flavor)` setzt `request.state.api_flavor`. `ExtraDep` ist `True` genau wenn Flavor `kss` ist. **Nicht** den URL-Pfad parsen.

### installations.py (Muster für jede Entität)

- `read_router`: 3API-Verben (GET Collection/Item). Handler nehmen `extra: ExtraDep`.
- `kss_router`: Extra-Verben (Installation: `PATCH /installations`). Nur unter `/api/kss` mounten. PATCH-Erfolg: 201 neu / 204 sonst, kein Body, kein Extra-Header. `ExtraDep` nur an GET.

PATCH **nicht** auf `read_router` legen — sonst OpenAPI und Runtime unter `/api/v1` (erfundene REST).

### main.py

Denselben `read_router` zweimal einhängen, `kss_router` nur einmal:

```python
app.include_router(read_router, prefix="/api/v1",
                   dependencies=[Depends(bind_flavor("v1"))])
app.include_router(read_router, prefix="/api/kss",
                   dependencies=[Depends(bind_flavor("kss"))])
app.include_router(kss_router, prefix="/api/kss",
                   dependencies=[Depends(bind_flavor("kss"))])
```

Kein Pfadparameter `/api/{tree}/…`. Keine Router-Factory, die zwei Klone baut. Kein generisches Resource/CRUD-Framework.

### deps.py

Defaults **einmal** in den Page-Dependencies, nicht in Handler-Signaturen. FastAPI in dieser Version erlaubt kein `Query(0, …)` innerhalb von `Annotated` an der Route; deshalb `Depends`:

```python
def _page_number(
    page_number: Annotated[int, Query(ge=0, alias="page[number]")] = 0,
) -> int:
    return page_number

def _page_size(
    page_size: Annotated[int, Query(ge=1, alias="page[size]")] = 65536,
) -> int:
    return page_size

PageNumber = Annotated[int, Depends(_page_number)]
PageSize = Annotated[int, Depends(_page_size)]
```

Handler: `page_number: PageNumber, page_size: PageSize` ohne `= 0` / `= 65536`.

## Neue Entität

1. Eine Datei `kss/api/<entity>.py` nach dem Installations-Muster.
2. Serializer in `jsonapi.py` (oder der Entitätsdatei) mit `extra=`; `kss:`-Keys nur wenn `extra`.
3. `read_router` in `main.py` unter beiden Prefixes mounten; `kss_router` nur wenn Extra-Verben existieren.
4. Pagination und Flavor nicht neu erfinden.

Installation liegt bereits auf diesem Layout. Pakete `api/v1/` / `api/kss/` nicht wiederherstellen.

Falls die Pakete trotzdem wieder auftauchen: umstellen wie früher (eine `installations.py`, dualer Mount, Pagination in `deps.py`, alte Pakete und `*_http.py` löschen). URLs unverändert; `test_api_installations.py` muss grün bleiben. PATCH darf unter `/api/v1` weder Runtime noch OpenAPI erscheinen.