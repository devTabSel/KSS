---
name: knx-semantik
description: >-
  KNX-Semantik for KSS: three sources (KNX IoT 3rd Party API, KIM ontology
  v2/v3, ETS .knxproj XML schema 23), identity join TTL↔0.xml, last_modified
  versioning, last_import, bus_pa_bindings/bus_ga_bindings, knx_master
  datafields, GroupRange, ChannelInstance, serial numbers. Use when analysing
  or extending persistence, implementing import, mapping telegrams at time t,
  or when the user mentions KIM, ontology, semantic export, knxproj, Loaded
  flags, or CompletionStatus.
---

# KNX-Semantik

## Mandatory delegation

Schema, Alembic and persistence modelling MUST be executed by the `Modellierer` subagent.
TTL/join, BUS-index fill and related import code MUST be executed by the `Representer` subagent.

When this skill is invoked:

1. Do NOT perform schema or import-fill in the current agent unless you are that subagent.
2. Delegate modelling to `Modellierer`.
3. Delegate import-fill to `Representer`.
4. Return the result to the user.

`APIler` reads this skill in full (same knowledge as Representer for names, join, temporal, BUS). HTTP remains skill `kss-api`. Fork edits remain skill `xknxproject` / **Representer**. If the split is unclear, ask the user.

Regelwerk für **Modellierer** (Schema), **APIler** (Namen/Join beim HTTP-Mapper) und **Representer** (TTL/Join, BUS-Fill). Modelle nicht ungefragt ändern; Feldliste zuerst mit dem Nutzer abstimmen. Import-Code nur auf explizite Anforderung (dann **Representer**).

## Ziel

KSS persistiert die Semantik, die Telegramme und Clients später brauchen — einmal aus `.knxproj` und TTL, nicht als parallele Welten. Pläne unter `.cursor/plans/` sind verbindlich, besonders [Temporale Semantik](../../plans/temporal-bus-semantics.md).

## Pläne

- [README](../../plans/README.md) — großes Ziel
- [PATCH Installation exports](../../plans/patch-installation-exports.md)
- [KSS and KNX 3rd Party API](../../plans/kss-and-knx-3rd-party-api.md)
- [Temporale Semantik](../../plans/temporal-bus-semantics.md)
- [HomeAssistant KNX Integration](../../plans/homeassistant-knx-integration.md)

## Quellen (normative Reihenfolge)

1. **3API** (`public-projects/knx-iot-3rd-party-api-schema/schemas/`, nicht `schemas-2020/`) — Kategorie 1.
2. **KIM** — [Downloads](https://support.knx.org/hc/en-us/articles/10386532582930-Downloads):
   - **v2 release** (ETS MaC): `https://update.knx.org/data/Semantics/ontology/v2/ontology.ttl`
   - **v3 WIP**: `https://schema.knx.org/2020/ontology?destination_format=ttl`
   - Local cache: `ontology-v2.ttl`, `ontology-latest.ttl` in this folder (do not dump into chat).
   - ETS Semantic Export: Export → Turtle / JSON-LD; file includes a copy of the ontology at export time.
3. **`.knxproj` XML schema 23** (namespace `http://knx.org/xml/project/23`). Instance: `P-*/0.xml`. Minimum ETS **6.4.1**.

Kategorie 3 = KIM und/oder knxproj, nicht in der 3API. Nie als offizielle 3API ausgeben.

## Persistieren

Alle **semantischen** Attribute, die in Ontologie, XSD oder beiden vorkommen und später Telegramme (Devices, GA, Functions, Locations, Trades) binden.

Weglassen: Download-Binaries, Crypto, BusAccess, Hashes, APDU-Zähler. Details: [reference.md](reference.md), [tables.md](tables.md).

Bei Unsicherheit: **Nutzer fragen**.

## Identity join (TTL ↔ 0.xml)

knxproj `@Id` z. B. `P-040E-0_DI-1`. TTL: **`prj:DI-1`**. Prefix `P-<ProjectId>-<InstallationIndex>_` ist XML-Namensraum. `ProjectInformation/@Guid` = TTL-Namespace = `installations.project_guid`.

`ets_id` = lokales Fragment (`DI-1`). Unique `(installation_id, ets_id)` bzw. `(device_id, ets_id)` für geräteinterne Objekte. `Puid` XML-only, nie wiederverwenden.

| Type | ets_id | TTL |
| --- | --- | --- |
| Installation | `P-0260-0` | `core:Installation` |
| Device | `DI-n` | `core:Device` |
| Space | `BP-n` | `loc:Building\|Floor\|Room\|Space` |
| GroupAddress | `GA-n` | `knx:FunctionPoint` (= 3API datapoint) |
| Function | `F-n` | `core:ApplicationFunction` (nicht `core:Functionality`) |
| Trade | `T-n` | nicht im TTL (Name am Device) |
| Area/Line/Segment | `A-n`/`L-n`/`S-n` | nicht im TTL |
| GroupRange | `GR-n` | nicht im TTL |
| ChannelInstance | `DI-n_CI-n` | `knx:Channel` |
| CommObject | `O-…_R-…` | `core:Datapoint` (nicht die GA) |

`prj:Site` ist nicht die Installation. `tag:lighting` ist kein Gewerk. `core:Functionality` nicht persistieren.

Gleiche Bedeutung in TTL und XML → **eine** Spalte. Zweites Format füllt dieselbe Identität.

## `last_modified` / `last_import` / BUS

Kanonisch: `kss.models.temporal` und [Temporale Semantik](../../plans/temporal-bus-semantics.md).

- **`last_modified`** (NOT NULL, PK-Teil): Objekt-LastModified, sonst Projekt-LastModified. Neue Version nur bei semantischem Diff.
- **`installations.last_import`**: Import-Uhr (UTC) bei PATCH.
- **BUS:** `bus_pa_bindings`, `bus_ga_bindings` mit echtem `last_downloaded` und passenden `*Loaded`-Flags. Sentinel `0001-01-01` nie speichern.

`GroupAddressStyle` ist immutable auf `installations`.

Telegramm zur Zeit `x`: BUS-Indizes, dann `E(entity, x)`.

## Channels

`ChannelInstance/@Id` → `ets_id`; `@RefId` → `catalog_ref`. Ohne ChannelInstances ist TTL `CI-n` nicht Baumordnung. Folders `PB-*` knxproj-only.

## Dateien lesen (Import)

| Input | Parse |
| --- | --- |
| `.knxproj` | `P-*/project.xml`, `P-*/0.xml`, `knx_master.xml` |
| `.ttl` | `prj:`-Individuen **vor** dem Ontology-Dump |

Manufacturer-XML nur für Channel-`RefId` / Produkttitel / CO-Katalogtext.

## Details

- Empirischer Join TTL↔knxproj: [reference.md](reference.md)
- Tabellen-Mapping: [tables.md](tables.md)
