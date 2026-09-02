# KSS and KNX 3rd Party API

URL-Vertrag und `src`-Layout. Skill `kss-api` (KSS-API), Agent **APIler**. Einordnung: [README](README.md).

Eltern: [PATCH Installation exports](patch-installation-exports.md). Temporal: [Temporale Semantik](temporal-bus-semantics.md). Clients: [HomeAssistant KNX Integration](homeassistant-knx-integration.md).

Großes Ziel: dieselbe Installation, dieselbe UUID, zwei Verträge — 3API-konform (`/api/v1`) oder KSS-erweitert (`/api/kss`). Clients (HA und andere) wählen den Baum; `src` dupliziert ihn nicht.

## Status

Umgesetzt für Installation. Weitere Entitäten analog, **keine** zweiten Pakete.

- `src/kss/api/installations.py` — `read_router` (GET) + `kss_router` (PATCH)
- `src/kss/api/flavor.py` — `bind_flavor` / `ExtraDep`
- `src/kss/api/deps.py` — Pagination-Defaults nur hier
- `src/kss/api/jsonapi.py` — `extra=` steuert `kss:` inkl. `kss:lastImport`

Pakete `src/kss/api/v1/` und `src/kss/api/kss/` sind verboten.

## Warum

Die zwei URL-Bäume sind ein **Vertrag**, kein zweites Paket. Doppelte Handler und hartes `extra=True/False` würden bei Location/Device/… kopiert.

## Soll

```
src/kss/api/
  deps.py            # page[number]=0, page[size]=65536 nur hier
  flavor.py          # bind_flavor → request.state.api_flavor; ExtraDep
  jsonapi.py         # extra= am Serializer
  installations.py   # read_router (GET) + kss_router (PATCH)
  <entity>.py        # später analog
```

`main.py` hängt denselben `read_router` unter `/api/v1` und `/api/kss` (`bind_flavor("v1")` bzw. `"kss"`); `kss_router` nur unter `/api/kss`.

| Baum | Vertrag |
| --- | --- |
| `/api/v1` | nur spezifizierte 3API. Collection/Item GET. Kein Datei-Ingest. Nur Kategorie-1. |
| `/api/kss` | dieselben Pfade und JSON:API-Hülle plus `kss:` und Extra-Verben. Aktuell = `max(last_modified)`. |

PATCH unter `/api/v1` weder Runtime noch OpenAPI.

## Nicht tun

- Modelle, Alembic, xknxproject-Semantik ändern (Modellierer / Importer / Forker)
- `/api/{tree}/…` als Pfadparameter
- Router-Factory mit zwei Klonen
- generisches Resource/CRUD-Framework
- Pakete `api/v1/` / `api/kss/` wiederherstellen
- OAuth / 3API-JSON-Schema ändern
