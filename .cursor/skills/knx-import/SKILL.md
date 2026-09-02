---
name: knx-import
description: >-
  Import ETS .knxproj (schema 23, ETS 6.4.1+) and Semantic Export TTL/JSON-LD
  into KSS identity+version tables. Use when implementing or changing importers,
  joining prj: fragments to 0.xml Ids, deriving last_modified from ETS
  LastModified, materializing bus_pa_bindings and bus_ga_bindings, mapping
  knx_master datafields, GroupAddressStyle/GroupRange, ChannelInstance, serial
  numbers, or telegram-to-datapoint_id lookup.
---

# KSS ETS import

Do **not** write importer code unless the user explicitly asks. This skill is the rulebook.

Do **not** change SQLAlchemy models here; models live in worktree/branch `KSS-DB-model`. Read those tables before inserting.

Minimum ETS: **6.4.1**, knxproj namespace `http://knx.org/xml/project/23`. Same project may arrive as ZIP `.knxproj` and as `.ttl`.

## Files to read

| Input | What to parse |
| --- | --- |
| `.knxproj` ZIP | `P-*/project.xml` (`ProjectInformation`), `P-*/0.xml` (installation), `knx_master.xml` (`MasterData/@Version`) |
| `.ttl` | `prj:` individuals **before** the bundled ontology dump; prefix `http://iot.knx.org/{Guid}#` |

Skip manufacturer application XML except when resolving Channel `RefId` / product title / CO catalogue text.

## Identity join (same DB row)

knxproj `@Id` = `P-<ProjectId hex>-<InstallationIndex>_<Type>-<Index>`.

TTL subject = **`prj:<Type>-<Index>`** (example `P-040E-0_DI-1` ↔ `prj:DI-1`).

Store `ets_id` = local fragment (`DI-1`). Optional reconstruct full Id from installation `knx_project_id` + `installation_index`. `Puid` XML-only, never reuse. Unique `(installation_id, ets_id)` for project-scoped objects. Device-local objects (channel, folder, comm object): unique `(device_id, ets_id)`.

`ProjectInformation/@Guid` = TTL namespace = `installations.project_guid`.

| Type | ets_id | TTL class |
| --- | --- | --- |
| Installation | `P-0260-0` | `core:Installation` |
| Device | `DI-n` | `core:Device` |
| Space | `BP-n` | `loc:Building\|Floor\|Room\|Space` |
| GroupAddress | `GA-n` | `knx:FunctionPoint` (= 3API datapoint) |
| Function | `F-n` | `core:ApplicationFunction` (not `core:Functionality`) |
| Trade | `T-n` | **not in TTL** (name only on device) |
| Area/Line/Segment | `A-n`/`L-n`/`S-n` | **not in TTL** |
| GroupRange | `GR-n` | **not in TTL** |
| ChannelInstance | `DI-n_CI-n` | `knx:Channel` — see channels |
| CommObject | `O-…_R-…` | `core:Datapoint` (not the GA) |

`prj:Site` (`loc:Site`) is **not** the installation. Synthetic location root; ignore dummy title/comment/`42`/`Unknown`. Optional: one `location_type` n/a with `at_type` containing `loc:Site`.

## One column per meaning

Same semantics in TTL and XML → one column. Fill from whichever export is present; second import updates the same identity.

| Meaning | knxproj | TTL |
| --- | --- | --- |
| CompletionStatus | `@CompletionStatus`, omit = `Undefined` | `core:state` |
| Device title | `@Name` if non-empty else product | `dct:title` |
| Installation title | `ProjectInformation/@Name` (Installation `@Name` often empty) | `dct:title` |
| IA | Area+Line+Device `@Address` | `knx:individualAddress` hex without `0x` (`10F8` = 1.0.248) |
| Serial | `@SerialNumber` base64 of 6 bytes | `core:serialNumber` `$`+hex — **same 6 bytes**, store hex |
| GA number | `@Address` int | `knx:groupAddress` |
| Trade on device | `DeviceInstanceRef` under `T-*` | `mac:assignedTrade` **name only**, not unique |

`tag:lighting` is not a trade. `core:Functionality` (UUID IRI, bag of COs) is not an ETS function — do not persist.

## `last_modified` / `last_import` / BUS

Kanonisch: `kss.models.temporal`, `plans/temporal-bus-semantics.md`.

- **`last_modified`** (NOT NULL, PK-Teil): ETS-Versionsschlüssel und 3API `lastModified`. Objekt-`LastModified`, sonst Projekt-`LastModified`. Neue Version nur bei semantischem Diff. Gleiches `(entity_id, last_modified)` → keine zweite Zeile.
- **`installations.last_import`**: Import-Uhr (UTC), bei PATCH-Ingest gesetzt.
- **BUS:** `bus_pa_bindings` (PA→Device) und `bus_ga_bindings` (GA+Device) mit `last_downloaded`. Befüllung beim Device-Import; Flags `*Loaded` auf `device_versions` steuern welche Zeilen geschrieben werden. Sentinel `0001-01-01` für `LastDownload` nie speichern.

`GroupAddressStyle` (`ThreeLevel`/`TwoLevel`/`Free`) is immutable on `installations` — never version it.

## Channels

Prefer `0.xml` `ChannelInstances`: `Id=P-040E-0_DI-65_CI-9` → `ets_id` `DI-65_CI-9` or `CI-9` scoped to device; `RefId` → `catalog_ref` (`CH-3` or `MD-…_CH-4`). Inactive instances may be absent from TTL.

Without `ChannelInstances` (test_A): TTL `CI-n` is **not** reliably tree order on modular devices — match via contained COs + `catalog_ref`.

Module channels in TTL may use `…_MD-1_M-1_MI-1_CI-1` instead of `CI-2`. Join via `ChannelInstance/@RefId` and CO `ChannelId`.

Folders: `GroupObjectTree` `Node[@Type=Folder]` `RefId` (`PB-47`), knxproj-only.

## Persist / skip

**Persist:** knx_master DPT/DPST/Format → datafields; FunctionTypes; DatapointRoles; SpaceUsages; MediumTypes; topology; trades + temporal device assignment; GroupRanges (temporal names); `ChannelInstance`; CO flags; `GroupAddressRef/@Role` (may be `DR-*` or UUID); Space `@Type` (XSD, not master); `@Usage` as `SU-*` **or** `tag:bedroom`; `DefaultLine`; `DistributionBoard`.

**Skip:** `LoadedImage`, `CheckSums`, `LastUsedAPDULength`, crypto keys, `BusAccess` secrets, RTF may be stored raw in `comment` / `installation_hints` (one field each).

## Telegram at time x

Lookup: installation + 16-bit destination + **bus-effective** time → `bus_ga_bindings` / `bus_pa_bindings`, dann `E(entity, x)` auf `*_versions`. Address reuse: whoever owned the integer at x.

## Details

Normative mapping, table intent, and WA53H10/test_A findings: [reference.md](reference.md) and modeller skill `knx-semantic-sources`.
