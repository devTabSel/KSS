---
name: knx-semantic-sources
description: >-
  KSS modelling from three sources — KNX IoT 3rd Party API, KIM ontology
  (ETS Semantic Export TTL/JSON-LD v2 release, v3 WIP), and ETS .knxproj XML
  schema v23. Use when analysing or extending persistence models for Device,
  Function, Location, Trade, Datapoint, GroupAddress, Installation; mapping
  TTL individuals to 0.xml Ids; deciding which ETS/KIM attributes to persist;
  or when the user mentions KIM, ontology, semantic export, knxproj, CompletionStatus.
---

# KNX semantic sources for KSS models

Do **not** change SQLAlchemy/Alembic models unless the user explicitly agrees the field list. Propose first.

## Sources (normative order)

1. **3API** (`public-projects/knx-iot-3rd-party-api-schema/schemas/`, not `schemas-2020/`) — Kategorie 1.
2. **KIM** — [Downloads](https://support.knx.org/hc/en-us/articles/10386532582930-Downloads):
   - **v2 release** (ETS MaC): `https://update.knx.org/data/Semantics/ontology/v2/ontology.ttl`
   - **v3 WIP**: newest at `https://schema.knx.org/2020/ontology?destination_format=ttl`
   - Local cache: `ontology-v2.ttl`, `ontology-latest.ttl` in this folder (do not dump into chat).
   - Docs: [KIM introduction](https://buildwithknxiot.knx.org/public-projects/knx-iot-docs/kim/introduction/), [Tags](https://buildwithknxiot.knx.org/public-projects/knx-iot-docs/kim/tags/), [Application Functions](https://buildwithknxiot.knx.org/public-projects/knx-iot-docs/kim/application-functions/).
   - ETS Semantic Export: menu Export → Turtle / JSON-LD; file **includes a copy of the ontology at export time**.
3. **`.knxproj` XML schema 23** (ETS 6.2+, namespace `http://knx.org/xml/project/23`): [Project Schema Documentation](https://support.knx.org/hc/de/article_attachments/17389755651474). Instance data: `P-*/0.xml`.

Kategorie 3 = KIM and/or knxproj fields not in 3API. Never present them as official 3API.

## What to persist

Persist **all semantic** attributes of an object that appear in the ontology, the XML schema, or both, if they can later bind **telegrams** to devices / group addresses / functions / locations / trades.

Skip **technically necessary** fields (download internals, crypto, bus-access machinery). See [reference.md](reference.md).

On uncertainty: **ask the user**, do not invent mappings.

## Identity join (TTL ↔ 0.xml)

knxproj `@Id` z. B. `P-040E-0_DI-1`. TTL-Individual: **`prj:DI-1`** (Objekttyp + Index). Der Prefix `P-<ProjectId>-<InstallationIndex>_` gehört zum XML-Namensraum, nicht zum TTL-Fragment. `ProjectInformation/@Guid` ist der TTL-Namespace (`http://iot.knx.org/{Guid}#`).

Type codes: [reference.md](reference.md).

## Modelling rules

- Identity table (3API UUID) + `ets_id` (knxproj `Id`) on identity, indexed.
- Semantic attributes on version rows: PK `(entity_id, _since)`, plus `_observable_since`. Same temporal rules as Installation.
- Same meaning in TTL and XML → **one column**, document both names.
- KIM tags (`tag:operatesForTrade`, `tag:hasLocationUsage`, `@type`) are first-class, not JSONB leftovers.
- 3API OpenAPI examples (`assignedTrade`, `tag:operatesForTrade`) are Kategorie 2 until the ontology class/property is cited.

## Workflow

3API + KIM + knxproj XSD → gap list vs current packet → **user review** → then model worktree.

Details: [reference.md](reference.md).
