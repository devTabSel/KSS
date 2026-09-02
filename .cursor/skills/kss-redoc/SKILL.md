---
name: kss-redoc
description: >-

  KSS-reDoc: archive live docs and chat notes into docs/evolving/, then
  rewrite two current doc trees from code, plans, and skills — docs/technical
  for further development and docs/fachlich for KSS users. Use when the user
  mentions Blubberer, reDoc, KSS-reDoc, evolving, fossil docs, _since,
  kss:since, or when live documentation must match the current Ist. Do not
  use for model, REST, fork, or plan edits.
---

# KSS-reDoc

## Mandatory delegation

This skill MUST be executed by the `Blubberer` subagent.

When this skill is invoked:

1. Do NOT perform the work in the current agent.
2. Delegate the complete task to the `Blubberer` subagent.
3. `Blubberer` must read and follow this entire skill.
4. Return the result of the `Blubberer` execution to the user.

`Blubberer` is the sole executor for this skill.

Regelwerk für Agent **Blubberer**. Zwei Live-Bäume, ein Archiv. Kein zweiter Orchestrator.

## Ziel

Leser-Doku beschreibt nur den **aktuellen Ist**. Entwicklungsspuren und Chat-Erkenntnisse liegen in `docs/evolving/`. Pläne, Skills und Agents bleiben Betriebssystem — nicht archivieren.

## Pläne

- [README](../../plans/README.md)
- [PATCH Installation exports](../../plans/patch-installation-exports.md)
- [KSS and KNX 3rd Party API](../../plans/kss-and-knx-3rd-party-api.md)
- [Temporale Semantik](../../plans/temporal-bus-semantics.md)
- [HomeAssistant KNX Integration](../../plans/homeassistant-knx-integration.md)

## Wahrheit (Reihenfolge)

1. **Code** — `src/kss/`, `alembic/versions/`, Tests
2. **Pläne** — `.cursor/plans/` (Soll und bewusste Lücken)
3. **Skills / Agents** — `.cursor/skills/`, `.cursor/agents/`

`docs/evolving/` ist **keine** Quelle für Präsens. Mapping-Tabellen, die im Code noch gelten, dürfen in `docs/technical/` neu stehen — ohne Worktree-Sprache und ohne Archäologie.

## Zwei Live-Bäume

| Baum | Leser | Inhalt |
| --- | --- | --- |
| `docs/fachlich/` | Nutzer von KSS (Clients, Betrieb, später HA) | Was KSS ist, welche Verträge existieren, was ingestiert und gelesen werden kann, was bewusst fehlt |
| `docs/technical/` | Weiterentwicklung | Schema, HTTP-Src, Ingest, Temporal/BUS, Alembic, Fork-Konsum, Paket-Mappings |

Root-`README.md` zeigt auf beide Bäume und auf `docs/evolving/`.

## Archiv-Protokoll

1. Betroffene **Live-Docs** (`docs/fachlich/`, `docs/technical/`) mit Datum nach `docs/evolving/` kopieren (z. B. `evolving/YYYY-MM-DD-…/` oder überschreiben der Museums-Kopien mit Archivvermerk).
2. Chat-Erkenntnisse und Zwischenstände, die während der Entwicklung entstehen, nach `docs/evolving/notizen/` (`YYYY-MM-DD-kurzthema.md`).
3. Beide Live-Bäume aus Code + Plänen + Skills **neu schreiben**.
4. Root-README anpassen, falls Einstieg veraltet ist.

Nicht nach `evolving/`: `.cursor/plans/`, `.cursor/skills/`, `.cursor/agents/`.

## Verboten im Präsens (Live-Docs)

| Nicht als Ist | Ist |
| --- | --- |
| `_since` / `_observable_since` / `INITIAL_SINCE` | `last_modified` + `last_import` |
| `kss:since` | `kss:lastImport` |
| Pakete `src/kss/api/v1/` + `api/kss/` | eine Datei je Entität, dualer Mount |
| parallele Modell-Worktrees als Default | Persistenz auf `main` |
| Eigenparser in KSS | Fork `xknxproject`, `parse(combine=False)` |
| Locations nach Name / Devices nach IA als Identität | `ets_id` / UUID |
| „Nicht nach `main` mergen ohne Freigabe“ als Modellstatus | Persistenz liegt auf `main` |
| „fünf Kopien `temporal.py`“ / fünf parallele `001_*` | eine Kette, `kss.models.temporal` |

Alte Zustände nur in `evolving/`. Pläne dürfen einmal „ersetzt `_since`“ als Migrationsnotiz sagen. Live-Docs nicht.

DDL-History in Alembic (`003_temporal_lm_bus.py`) darf `_since` enthalten — das ist Migration, keine Leser-Doku.

## Stil

Knapp. Kein Roman. Fachlich ohne SQLAlchemy-Klassen und ohne Src-Pfade, außer Nutzer brauchen einen Endpunkt. Technisch mit Pfaden und Tabellen. Bewusste Lücken explizit (TTL 501, kein OAuth, HTTP nur Installation, Device-Ingest offen).

## Nicht tun

- Modelle, REST, Fork, Tests, Pläne ändern
- `evolving/` als Ist zitieren
- die zwei Live-Bäume zu einer Datei zusammenziehen
