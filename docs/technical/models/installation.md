# Installation

3API `installation` plus knxproj-Identität und knx_master-Katalog. HTTP: GET Collection/Item auf beiden Prefixes; PATCH `.knxproj` und `.ttl` unter `/api/kss`. JSON-GET `?at=` und Datei-Export (`.ttl` / `.knxproj`) nur `/api/kss` — [export.md](../export.md).

## Tabellen

- `installations` — UUID, `ets_id` (`P-040E-0`), `project_guid` (TTL-Namespace), `knx_project_id`, `installation_index`, `group_address_style` (immutable: ThreeLevel/TwoLevel/Free), `last_import`.
- `installation_versions` — 3API-Attribute; `completion_status` (3API `state`); `master_data_version`; `project_type` (XSD 23 `ProjectType_t`); PK `(installation_id, last_modified)`.
- `installation_subscriptions` — current-state, `subscription_id` ohne FK (Subscription-Entität fehlt).
- Katalog current-state, Unique `(installation_id, ets_id)`: DPT, DPST, datafields (3API), FunctionTypes, DatapointRoles, SpaceUsages, MediumTypes.
- `master_project_types` — sprachabhängiger ProjectType-Katalog, Unique `(installation_id, ets_id, language_code)`. `ets_id` ist das XML-Token (`Family House`), nicht die UI-Übersetzung (`Familienhaus`).

Titel: `ProjectInformation/@Name` / TTL `dct:title`. `prj:Site` ist nicht die Installation. knx_master nur aus knxproj.

TTL-Ingest schreibt Installation selbst (ohne `upsert_installation_from_info`) und erhält knxproj-only Spalten beim Join. Details: [ingest.md](../ingest.md). Datei-GET rekonstruiert den Stand zu `t` aus den Versionen; Originaldateien werden nicht gespeichert.

## Mapping (ETS UI / knxproj / TTL / 3API / DB / Kategorie)

| ETS UI (de) | knxproj (XSD 23) | KIM / TTL | 3API | DB-Spalte | Kat. |
| --- | --- | --- | --- | --- | --- |
| Projektname | `ProjectInformation/@Name` | `dct:title` | `attributes.title` | `installation_versions.title` | 1 |
| Beschreibung | `ProjectInformation/@Comment` (RTF, `xs:string`) | `core:comment` an `core:Installation` | `attributes.comment` | `installation_versions.comment` | 1 |
| Vertragsnummer | `ProjectInformation/@ContractNumber` | `knx:contractNumber` | `attributes.contractNumber` | `installation_versions.contract_number` | 1 |
| Projektnummer | `ProjectInformation/@ProjectNumber` | `knx:projectInstallationNumber` | `attributes.projectInstallationNumber` | `installation_versions.project_installation_number` | 1 |
| — | `ProjectInformation/@LastModified` | `core:lastModified` | `attributes.lastModified` | `installation_versions.last_modified` | 1 |
| Fertigstellungsstatus | `@CompletionStatus` (Omit → Undefined) | `core:state` | `attributes.state` | `installation_versions.completion_status` | 1 (= CompletionStatus) |
| Projekttyp (z. B. **Familienhaus**) | `ProjectInformation/@ProjectType` (`Family House`) | *nicht in KIM* | *nicht in 3API* | `installation_versions.project_type` + `master_project_types` | 3 |
| Gruppenadressenstil | `@GroupAddressStyle` | — | — | `installations.group_address_style` | 3 |
| — | `Project/@Id` + InstallationIndex | `prj:P-040E-0` | — | `installations.ets_id` | 3 |
| — | `ProjectInformation/@Guid` | TTL-Namespace | — | `installations.project_guid` | 3 |

JSON:API unter `/api/kss` zusätzlich: `kss:etsId`, `kss:projectGuid`, `kss:installationIndex`, `kss:groupAddressStyle`, `kss:masterDataVersion`, `kss:projectType`, `kss:lastImport`.

## Eine Spalte pro Bedeutung

- Projektnummer: UI / `@ProjectNumber` / `knx:projectInstallationNumber` / 3API `projectInstallationNumber` → `project_installation_number`.
- Vertragsnummer: analog → `contract_number`.
- Beschreibung: XSD 23 `ProjectInformation` hat kein Kind `Description`; `@Comment` = 3API `comment` = KIM `core:comment` → eine Spalte `comment`.

## Projekttyp (Kategorie 3)

XSD 23 `ProjectType_t`. Persistenz nullable. Versionszeile speichert den XML-Token; UI-Label (`Familienhaus`) nur im Katalog `master_project_types`, sobald eine maschinenlesbare Quelle existiert. `knx_master.xml` enthält diesen Katalog nicht.

`group_address_style` bleibt Identität/immutable.

Runtime-`value` auf datafields wird nicht persistiert.
