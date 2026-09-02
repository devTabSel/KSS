# Installation

3API `installation` plus knxproj-Identität und knx_master-Katalog. Nicht nach `main` mergen ohne Freigabe.

Archiviert nach `docs/evolving/` am 2026-09-02 (reDoc). Nicht verbindlich.

## Tabellen

- `installations` — UUID, `ets_id` (`P-040E-0`), `project_guid` (TTL-Namespace), `knx_project_id`, `installation_index`, **`group_address_style`** (immutable: ThreeLevel/TwoLevel/Free).
- `installation_versions` — 3API-Attribute; **`completion_status`** statt `state`; `master_data_version`; **`project_type`** (XSD 23 `ProjectType_t`).
- `installation_subscriptions` — current-state, `subscription_id` ohne FK (Subscription-Entität fehlt).
- Katalog current-state, Unique `(installation_id, ets_id)`: DPT, DPST, **datafields** (3API), FunctionTypes, DatapointRoles, SpaceUsages, MediumTypes.
- **`master_project_types`** — sprachabhängiger ProjectType-Katalog, Unique `(installation_id, ets_id, language_code)`. `ets_id` ist das XML-Token (`Family House`), nicht die UI-Übersetzung (`Familienhaus`).

Titel: `ProjectInformation/@Name` / TTL `dct:title`. `prj:Site` ist nicht die Installation.

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

WA53H10 `P-040E/project.xml` Zeile 4: `ProjectType="Family House"`; `ProjectNumber`/`ContractNumber` fehlen (nullable). `Comment` ist leeres RTF. TTL `prj:P-040E-0` / `prj:P-0260-0` hat `dct:title`, `knx:macVersion`, `core:containsAsset`, `core:lastModified`, `core:state` — keine `knx:contractNumber`/`knx:projectInstallationNumber`-Tripel, obwohl die Ontologie die Properties definiert.

## Kategorie

| Spalte | Kat. |
| --- | --- |
| id, title, comment, contract_number, last_modified, project_installation_number, type_description | 1 (3API) |
| completion_status | 1 als 3API `state`, semantisch = CompletionStatus / `core:state` |
| ets_id, guid, style, master_data_version, Katalog, **project_type** | 3 |

Runtime-`value` auf datafields wird nicht persistiert. Manufacturers-Keys, MaskVersions-Interna, Languages (außer ProjectType-Katalog): weggelassen.

## Semantisch gleiche Felder: eine Spalte

- **Projektnummer:** ETS-UI „Projektnummer“, knxproj `@ProjectNumber`, KIM `knx:projectInstallationNumber`, 3API `projectInstallationNumber` → nur `project_installation_number`. Keine zweite Spalte.
- **Vertragsnummer:** ETS-UI „Vertragsnummer“, `@ContractNumber`, `knx:contractNumber`, 3API `contractNumber` → nur `contract_number`.
- **Beschreibung:** XSD 23 `ProjectInformation` hat **kein** Kind `Description` (Kinder: HistoryEntries, ToDoItems, ProjectTraces, DeviceCertificates, Tags). Attribut `@Comment` = 3API `comment` = KIM `core:comment`. `dct:description` kommt in Instanz-TTL an der Installation nicht vor (nur an `prj:Site` und Ontologie-Klassen). Eine Spalte `comment`.

## Projekttyp (Kategorie 3)

XSD 23 `ProjectType_t` (Project Schema Documentation 01.00.00, „User interface specific (icons only)“). XML-Default bei Omit: `Other (Commercial)`. Persistenz bleibt nullable (leere optionale Felder).

Enumerationswerte (Join-Schlüssel / `ets_id` / `project_type`):

Residential: `Apartment`, `Family House`, `Villa`, `Other (Residential)`.
Commercial: `Hotel`, `Airport`, `Office Building`, `Educational`, `Leisure`, `Entertainment`, `Public Building`, `Health Care`, `Other (Commercial)`.
Other: `Manufacturer`, `City Project`, `Transportation`, `Other (Other)`.

WA53H10: XML `Family House`, ETS UI (de) **Familienhaus**. test_A 5: `Other (Other)`.

### Sprachabhängiger Katalog

`master_project_types (installation_id, ets_id, language_code, name)` plus UUID-PK wie die übrigen `master_*`-Tabellen. Unique `(installation_id, ets_id, language_code)`. Check: `ets_id` ∈ `ProjectType_t`, `language_code` mindestens zwei Zeichen (ETS `de-DE` / kürzer `en`), `name` nicht leer. Index `ix_master_project_types_installation_id`. Current-state, nicht historisiert. Muster `language_code` + übersetzter Text ist auf andere Master-Kataloge übertragbar.

Beispiel: `ets_id='Family House'`, `language_code='en-US'`, `name='Family House'`; dieselbe Installation `language_code='de-DE'`, `name='Familienhaus'`. Die Versionszeile speichert nur den XML-Token.

### Quellenlücke Übersetzungen

`knx_master.xml` von WA53H10 (`research/WA53H10/` und `C:\ProgramData\Knx\XML\project-23\`) enthält **kein** ProjectType-Katalog und **keine** `Languages/TranslationElement`-Einträge für `Family House` / `Familienhaus`. KIM `ontology-v2.ttl` / `ontology-latest.ttl` definieren kein `knx:projectType`. Die englischen Tokens stehen in XSD 23; die deutschen UI-Labels kommen aus der ETS-Lokalisierung, nicht aus knx_master. Der Importer kann die Katalogtabelle später aus ETS-UI/KIM füllen, sobald eine maschinenlesbare Quelle gefunden ist. Bis dahin bleibt die Tabelle das persistente Ziel; der XML-Token auf der Version ist unabhängig davon Pflicht für den Join.

`group_address_style` bleibt Identität/immutable, nicht auf der Version.
