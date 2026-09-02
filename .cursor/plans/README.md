# Pläne

Arbeitspläne unter `.cursor/plans/`. Sie konkretisieren das **große Ziel** und sind für alle Agents und Skills verbindlich.

## Großes Ziel

KSS ist die **zentrale temporale Semantikquelle** für KNX-Installationen.

- ETS-Exporte (`.knxproj`, später TTL/JSON-LD) werden **einmal** ingestiert (`PATCH /api/kss/installations`).
- Persistenz trennt **ETS-Versionen** (`last_modified`) und **BUS-Wirksamkeit** (`bus_pa_bindings`, `bus_ga_bindings`, `last_downloaded`).
- Clients — zuerst die **Home Assistant KNX Integration**, danach andere IoT-Stacks — **lesen** Semantik und importieren nicht selbst.
- `/api/v1` bleibt die offizielle **KNX IoT 3rd Party API**; `/api/kss` ist dieselbe Ressource plus Historie und `kss:`-Attribute.
- Telegramme zur Zeit `t` nutzen BUS-Indizes, dann ETS-Lookup `E(entity, t)`.

Jede Arbeit (Modell, HTTP, Import) muss dieses Ziel voranbringen, nicht nur die lokale Entität.

Live-Doku (Ist): `docs/fachlich/` und `docs/technical/`. Archiv und Chat-Notizen: `docs/evolving/` — nicht verbindlich. Nach Ist-Änderung Agent **Blubberer** (Skill `kss-redoc`).

## Dateien

| Datei | Inhalt | Stand |
| --- | --- | --- |
| [kss-modellierung.md](kss-modellierung.md) | **KSS Modellierung** — kanonische Feldlisten aller Persistenz-Pakete (Installation, MasterData, Location/Function, Topology, Device, Datapoint, Trade, BUS) | Feldlisten übernommen; Alembic erst auf explizite Anforderung, Paket für Paket, Modellierer |
| [patch-installation-exports.md](patch-installation-exports.md) | **PATCH Installation exports** — Ingest `.knxproj`/TTL, Installation zuerst, weitere Entitäten analog | Installation knxproj umgesetzt; Location…Trade und TTL offen |
| [trades.md](trades.md) | **Trades** — knxproj-Gewerkbaum vs. TTL-Name/Tags am Device; kein Auto-Join; Merge erst in Nutzerbearbeitung | Plan; Schema-Ist ohne TTL-Namensfeld; Import offen |
| [kss-and-knx-3rd-party-api.md](kss-and-knx-3rd-party-api.md) | **KSS and KNX 3rd Party API** — verbindliches GET-Soll: Collection/Item, `links.related`, Nested, Filter, Node synthetisch, `meta.@type` vs Tags; URL-Layout | Ist-GET Übergang; Soll für alle Agents |
| [temporal-bus-semantics.md](temporal-bus-semantics.md) | **Temporale Semantik** — `last_modified`-PK, `last_import`, BUS-Indizes, Erkenntnisse A–E | Schema umgesetzt; Device-Import (Representer) und Telegramm-API offen |
| [homeassistant-knx-integration.md](homeassistant-knx-integration.md) | **HomeAssistant KNX Integration** — HA und andere Clients lesen KSS statt lokalem knxproj-Parse | Richtungsplan, nicht jetzt implementieren |

Pfade in den Plänen sind relativ zum KSS-Repo (`devTabSel/KSS/`), Workspace-Pfade zu `devTabSel/xknxproject`, `public-projects/`, `research/` relativ zum Workspace-Root `dev/project/KSS/`.
