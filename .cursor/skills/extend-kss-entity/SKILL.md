---
name: extend-kss-entity
description: >-
  Orchestrate extending the next KSS entity after Installation (Location,
  Device, Datapoint, Topology, Trade). Use when the user wants the next
  resource modelled and exposed like Installation: sources first, then
  modeller (persist only), then fAPIen (fork extras, temporal mapper,
  one HTTP module per entity mounted at /api/v1 and /api/kss). Do not
  recreate src/kss/api/v1 or api/kss packages. Do not use for OAuth, 3API
  schema edits, or unsolicited model/REST changes.
---

# Extend a KSS entity

Follow `.cursor/agents/extensioner.md`. Do not model or write REST yourself.

HTTP-Src ist Skill `kss-http-layout`: URL-Paar `/api/v1` + `/api/kss` als Mount-Prefixes, **eine Datei je Entität**. Keine Pakete `api/v1/` und `api/kss/`.

1. Read skills `kss-http-layout`, `knx-semantic-sources`, and `knx-import`.
2. Confirm the field list with the user from 3API `schemas/`, knxproj XSD 23 + instance, and KIM/TTL. Separate ETS UI text from XML tokens.
3. Commission `.cursor/agents/modeller.md` in a worktree: SQLAlchemy + Alembic + tests + package docs only. Wait for approval before merge.
4. After model approval, commission `.cursor/agents/fAPIen.md`: additive xknxproject `info` keys, one `parse()`, KSS `parse(combine=False)`, temporal persist, one module `kss/api/<entity>.py` mounted at both prefixes (`read_router` twice, `kss_router` only under `/api/kss`). Do not recreate packages `api/v1/` / `api/kss/`.

knxproj XML extract lives in the xknxproject fork (fAPIen). TTL import later fills the same identity rows. Do not invent translations missing from knx_master/KIM.
