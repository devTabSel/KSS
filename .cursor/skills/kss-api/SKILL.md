---
name: kss-api
description: >-
  KSS-API: /api/v1 (official 3API) and /api/kss (same resources plus kss:
  and extra verbs) are FastAPI mount prefixes of one module per entity, not
  packages api/v1/ and api/kss/. Flavor/ExtraDep, pagination only in deps.py.
  Use when adding or changing JSON:API routes, PATCH ingest, ExtraDep,
  flavor, include_router, or a new entity HTTP module, or when the user
  mentions KSS-API. Do not recreate src/kss/api/v1 or api/kss. Do not use
  for OAuth or 3API schema edits.
---

# KSS-API

## Mandatory delegation

This skill MUST be executed by the `APIler` subagent.

When this skill is invoked:

1. Do NOT perform the work in the current agent.
2. Delegate the complete task to the `APIler` subagent.
3. `APIler` must read and follow this entire skill.
4. Return the result of the `APIler` execution to the user.

`APIler` is the sole executor for this skill.

Agent **APIler** führt den Vertrag aus. Plan: [kss-and-knx-3rd-party-api.md](../../plans/kss-and-knx-3rd-party-api.md). Skill zuerst lesen, bevor REST geschrieben wird.

## Ziel

KSS enthält die KNX IoT 3rd Party API und erweitert sie. Clients (Home Assistant KNX Integration und andere) wählen `/api/v1` oder `/api/kss`; `src` dupliziert die Bäume nicht. Alle Pläne unter `.cursor/plans/` gelten.

## Pläne

- [README](../../plans/README.md) — großes Ziel
- [PATCH Installation exports](../../plans/patch-installation-exports.md)
- [KSS and KNX 3rd Party API](../../plans/kss-and-knx-3rd-party-api.md)
- [Temporale Semantik](../../plans/temporal-bus-semantics.md)
- [HomeAssistant KNX Integration](../../plans/homeassistant-knx-integration.md)

## URL-Vertrag

| Baum | Vertrag |
| --- | --- |
| `/api/v1` | nur spezifizierte 3API. Collection/Item GET. Kein Datei-Ingest. JSON:API, nur Kategorie-1. |
| `/api/kss` | dieselben relativen Pfade und 3API-Verben **plus** `kss:`. Extra-Verben nur hier. |

Pagination: `page[number]` Default 0, `page[size]` Default 65536 — **nur** in `kss/api/deps.py`. Collection-`meta.collection` immer. Item: `data.type`, `data.id`, `attributes.title` Pflicht. `relationships` weglassen, solange leer. Aktuell = `max(last_modified)`. Fehlerhülle analog `Errors.json`.

## Src-Soll

```
src/kss/api/
  deps.py            # PageNumber / PageSize; SessionDep
  flavor.py          # bind_flavor, ExtraDep
  jsonapi.py         # Hülle, Serializer extra=
  installations.py   # read_router + kss_router (PATCH)
  <entity>.py        # analog, eine Datei je Entität
```

Verboten: `src/kss/api/v1/`, `src/kss/api/kss/`, dünne Zwillinge nur für `extra=True/False`.

### flavor.py

`Flavor = Literal["v1", "kss"]`. `bind_flavor(flavor)` setzt `request.state.api_flavor`. `ExtraDep` ist `True` genau wenn Flavor `kss` ist. **Nicht** den URL-Pfad parsen.

### installations.py (Muster)

- `read_router`: 3API-Verben. Handler nehmen `extra: ExtraDep`.
- `kss_router`: Extra-Verben (Installation: `PATCH /installations`). Nur unter `/api/kss`. PATCH-Erfolg: 201 neu / 204 sonst, kein Body. `ExtraDep` nur an GET.

PATCH **nicht** auf `read_router` — sonst unter `/api/v1`.

### main.py

```python
app.include_router(read_router, prefix="/api/v1",
                   dependencies=[Depends(bind_flavor("v1"))])
app.include_router(read_router, prefix="/api/kss",
                   dependencies=[Depends(bind_flavor("kss"))])
app.include_router(kss_router, prefix="/api/kss",
                   dependencies=[Depends(bind_flavor("kss"))])
```

Kein Pfadparameter `/api/{tree}/…`. Keine Router-Factory. Kein generisches CRUD-Framework.

### deps.py

Defaults **einmal** in Page-Dependencies (`Depends`), nicht `Query(0)` in `Annotated` an der Route.

Handler: `page_number: PageNumber, page_size: PageSize` ohne `= 0` / `= 65536`.

## Neue Entität

1. Eine Datei `kss/api/<entity>.py` nach dem Installations-Muster.
2. Serializer mit `extra=`; `kss:`-Keys nur wenn `extra` (inkl. `kss:lastImport` wo zutreffend).
3. `read_router` unter beiden Prefixes; `kss_router` nur bei Extra-Verben.
4. Pagination und Flavor nicht neu erfinden.

Installation liegt bereits auf diesem Layout. Pakete `api/v1/` / `api/kss/` nicht wiederherstellen.
