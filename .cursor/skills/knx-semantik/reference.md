# TTL ↔ knxproj

Korpus `research/` (Workspace-Root). XSD-Analyse: **alle** `*.knxproj`. Ontologie: **alle** `*.ttl`. Instanz-Fakten unten mit Herkunft kennzeichnen; Join-Regeln gelten projektübergreifend.

- **WA53H10** — produktiv, groß, komplex. `research/WA53H10.knxproj` / `research/WA53H10/` (`P-040E/0.xml`) und `research/WA53H10.ttl` (`prj: <http://iot.knx.org/666d92fe-6df1-445e-8c0a-a9be732a8c3f#>`, Installation `prj:P-040E-0`).
- **`test_A*`** — Reverse Engineering (Namenskollisionen, Löschen+Neuanlage, Rename, IDs/`Puid`). Dateiname = Szenario. test_A 5: `P-0260/0.xml`, Guid `d0eb6c35-7a1e-41dd-8832-105ae1964af1`, Installation `prj:P-0260-0`.

TTL-Präfix: `prj: <http://iot.knx.org/{ProjectInformation/@Guid}#>`.

## Join-Schlüssel

knxproj `@Id` = `P-<ProjectId>-<InstallationIndex>_DI-n`. TTL-Subject = **`prj:DI-n`** (Objekttyp + Index, ohne XML-Präfix). WA53H10: `P-040E-0_DI-1` → `prj:DI-1`. test_A: `P-0260-0_DI-2` → `prj:DI-2`.

Gleiches Muster: `BP-n`, `GA-n`, `F-n`, `T-n` (Trades **nicht** als TTL-Individuen). Installation: `prj:P-<ProjectId>-<Index>`.

`Puid` steht nur in der XML; nach Löschen+Neuanlage (test_A 2) neue `Puid`/`ets_id`, nicht wiederverwenden.

## `core:state` = CompletionStatus

TTL `core:state` = knxproj `@CompletionStatus`. Fehlt das XML-Attribut → XSD-Default `Undefined`. Sentinel `core:state "Unknown"` nur am synthetischen `prj:Site` (nicht in `0.xml`).

WA53H10 Installation: `"Editing"`; Locations/Devices gemischt (`Accepted`, `Undefined`, …). test_A 5: überall `"Undefined"` (Attribut in der XML omit).

## `tag:lighting` ≠ Gewerk

`tag:lighting` ist ein KIM-**Trade-Tag** (Anwendungsdomäne). ETS-Gewerke sind Projektinstanzen `Trade/@Id` / `@Name`. 3API hat **keinen** Resource-Typ `trade`. OpenAPI `assignedTrade` / `tag:operatesForTrade` sind Kategorie-2-Beispiele.

`mac:assignedTrade` am Device ist der **Name-String** des XML-Gewerks, keine Tag-IRI. WA53H10 z. B. `"BUS_DPS1280"`. test_A 5: `"Gewerk 2"`; zwei XML-Gewerke heißen beide `"Gewerk 1"` (`T-3`, `T-4`) — der Name ist **nicht eindeutig**.

Zwei Importwege, **kein automatischer Join** (Plan [Trades](../../plans/trades.md)): knxproj → `trades`/`trade_devices` (`T-n`, `DeviceInstanceRef`); TTL → Device-String `mac:assignedTrade` plus `tag:operatesForTrade` am tragenden Subjekt. Zusammenführung erst in späterer Nutzerbearbeitung.

## Was der Semantic Export **nicht** enthält (nur knxproj)

- Topologie-Individuen `A-` / `L-` / `S-` (IA kodiert Area/Line/Device; test_A `"1002"` = hex 1.0.2, WA53H10 z. B. `"10F0"`)
- Trade-Individuen `T-` (nur `mac:assignedTrade` am Device)
- `CommunicationPartLoaded` / andere `*Loaded` (`core:lastDownloaded` Sentinel `0001-01-01` ist kein Download)
- Leeres Device-`@Name`: TTL `dct:title` fällt auf **Produktnamen** zurück

Functions `F-n` **sind** in WA53H10 (`prj:F-1` …). test_A 5 hatte keine — das ist kein Ontologie-Loch.

## Gemeinsame Semantik (Felder, 3API egal)

Nur was in **beiden** Formaten vorkommt oder klar aufeinander abbildbar ist.

### Installation

| Feld | TTL | knxproj |
| --- | --- | --- |
| Join | `prj:P-<ProjectId>-<Index>` | `Project/@Id` + Installation |
| Titel | `dct:title` | `ProjectInformation/@Name` |
| lastModified | `core:lastModified` | `ProjectInformation/@LastModified` (identischer Timestamp) |
| state | `core:state` | `@CompletionStatus` (Omit → Undefined) |

WA53H10: `prj:P-040E-0`, Titel `"WA53H10"`, state `"Editing"`. test_A: `prj:P-0260-0`, Titel `"test_A"`, state `"Undefined"`.

### Location (Space)

| Feld | TTL | knxproj |
| --- | --- | --- |
| Join | `prj:BP-n` | `Space/@Id` → `BP-n` |
| Titel | `dct:title` | `@Name` |
| Typ | `a loc:Building\|Floor\|Room\|Space` | `@Type` (`Building`, `Floor`, `Room`, `BuildingPart`→`loc:Space`) |
| state | `core:state` | `@CompletionStatus` |

### Device

| Feld | TTL | knxproj |
| --- | --- | --- |
| Join | `prj:DI-n` | `DeviceInstance/@Id` → `DI-n` |
| Titel | `dct:title` | `@Name` wenn gesetzt, sonst Produkt `dct:title` |
| Kommentar | `core:comment` | `@Comment` |
| lastModified | `core:lastModified` | `@LastModified` (identisch inkl. Ticks) |
| lastDownloaded | `core:lastDownloaded` | `@LastDownload` (fehlt XML → TTL MinDate) |
| state | `core:state` | `@CompletionStatus` |
| Individualadresse | `knx:individualAddress` hex-String (test_A `"1002"`, WA53H10 z. B. `"10F0"`) | Area.`@Address` + Line.`@Address` + Device.`@Address` |
| Produkt | `core:hasProduct` → `prj:{ProductRefId}` | `@ProductRefId` |
| Applikation | `core:hosts` → `prj:DI-n_{ApplicationId}` | `@Hardware2ProgramRefId` / ApplicationProgram |
| Gewerk-Name | `mac:assignedTrade` (String) | `Trade/@Name` der Zuordnung (nicht eindeutig) |

### GroupAddress / FunctionPoint + Datapoint

| Feld | TTL | knxproj |
| --- | --- | --- |
| Join GA | `prj:GA-n` | `GroupAddress/@Id` → `GA-n` |
| Titel | `dct:title` | `@Name` |
| Numerische GA | `knx:groupAddress` | `@Address` |
| DPT | `knx:datapointType knx:bool` | `@DatapointType` `DPST-1-2` |
| Security-Modus | `knx:securityMode` "Auto" | `@Security` Default Auto |
| Datapoint-Join | `…_O-…_R-…` | `ComObjectInstanceRef/@RefId` |
| Datapoint-Titel | `dct:title` (test_A z. B. `"BASE_Heartbeat"`) | Katalog / CO (nicht Instanz-Attribut) |
| Flags | `core:readable`/`writable`, `mac:configFlags` "CRT" | CO-Flags (test_A 5: nicht in 0.xml überschrieben) |
| GA gruppiert CO | `core:groups` | `ComObjectInstanceRef/@Links` (test_A `"GA-2"`) |

### GroupAddressStyle und GroupRange (nicht dreistufig fest verdrahtet)

`ProjectInformation/@GroupAddressStyle` ist `ThreeLevel` | `TwoLevel` | `Free` und **ändert sich während der Projektlebensdauer nicht**. Persistenz: eine Spalte auf der Installations-**Identität** (`installations.group_address_style`), nicht auf GA-Versionen, nicht historisiert.

Die Gruppenadresse selbst ist immer die 16-Bit-Zahl `GroupAddress/@Address` / TTL `knx:groupAddress` (`0…65535`). Keine Spalten `hauptgruppe` / `mittelgruppe` / `adresse`. Die Anzeige (`1/2/3`, `1/1234`, `1234`) ist eine Funktion aus Stil + Rohwert:

| Stil | Bits | Anzeige |
| --- | --- | --- |
| ThreeLevel | 5 + 3 + 8 | `main/middle/sub` |
| TwoLevel | 5 + 11 | `main/sub` |
| Free | 16 | Dezimal |

Namen der Ebenen liegen auf **GroupRange** (`GR-*`, nur knxproj; TTL hat keine Range-Individuen): Identität `group_ranges` + **`group_range_versions`** (Name, Kommentar, Description, `parent_group_range_id`, `range_start`/`range_end`). Umbenennen einer Haupt-/Mittelgruppe ist eine Version, kein neues Objekt. Tiefe ist nicht fix: ThreeLevel typisch 2 Range-Ebenen, TwoLevel eine, Free keine oder nur optionale Intervalle. Die GA hängt am innersten Range (`group_range_id` auf der GA-**Version**, nullable — ein Umhängen ist historisiert).

**Id ≠ Busadresse.** `GroupAddress/@Id` (`GA-17296`) und `@Puid` bleiben, wenn der Nutzer in ETS nur `@Address` ändert. Neue Versionszeile derselben Datapoint-Identität, Spalte `group_address` wechselt (z. B. 30720 → 30750). Löschen+neu anlegen erzeugt eine neue `GA-*`/`Puid`. TTL-Join bleibt `prj:GA-17296`.

**Neu programmieren:** Auf dem Bus steht die 16-Bit-Adresse plus die Associationstabelle (KO↔GA), nicht der ETS-Name. Namensänderung an Range/GA braucht kein Device-Download. Änderung von `group_address` oder der Kante `comm_object_datapoints` schon: ETS setzt i. d. R. `CommunicationPartLoaded=false`, bis der Communication-Part geladen ist (`LastDownload`). BUS-Wirksamkeit: [Temporale Semantik](../../plans/temporal-bus-semantics.md) (`bus_ga_bindings` / `bus_pa_bindings`). ETS-Semantik: `E(entity, t)` auf `last_modified`.

WA53H10 ist ThreeLevel, z. B. `GR-49` Name `EGD` `2048…4095` (Haupt 1) mit Kind `GR-65` `SRV` `2048…2303` (Mittel 0). `GA-17296` hat `Address="30720"` unabhängig von der Id.

### Channel / Product (TTL-reich, XML-teilweise)

| Feld | TTL | knxproj |
| --- | --- | --- |
| Channel | `prj:DI-n_CI-n` `knx:Channel` | `GroupObjectTree/Node[@Type=Channel]` |
| Bestellnummer | `core:orderNumber` am Product | Hardware/Catalog, nicht DeviceInstance |
| Hersteller | `core:manufacturer` | Master/Catalog |

## Nur knxproj (trotzdem persistieren, Nutzerwunsch)

**Gewerke** temporal: `Trade` Hierarchie + `DeviceInstanceRef`. Join `T-n`. Name darf kollidieren.

**Topologie** eigenes Paket: Area `A-n`, Line `L-n`, Segment `S-n` (`MediumTypeRefId`), Device hängt am Segment. TTL liefert das nur indirekt über IA + `core:mediaType` am Produkt.

**Download-Semantik:** [Temporale Semantik](../../plans/temporal-bus-semantics.md). `*Loaded`-Flags nur XML. BUS-Index-Zeile nur bei Flag **und** echtem `LastDownload`; `core:lastDownloaded` MinDate allein reicht nicht.

## Beziehungen (beide Formate bzw. XML-only)

| Kante | TTL | knxproj |
| --- | --- | --- |
| Location → Kind | `loc:hasFloor` / `hasRoom` / `hasSpace` / `hasLocation` | verschachteltes `Space` |
| Location → Device | `loc:containsEquipment` | `DeviceInstanceRef` |
| Installation → Device | `core:containsAsset` | Topology enthält DeviceInstance |
| Device → Channel | `knx:hasChannel` | GroupObjectTree Channel-Nodes |
| Channel → Datapoint | `core:hasPoint` | Node `@GroupObjectInstances` |
| ApplicationProgram → Channel | `core:implements` | — |
| FunctionPoint → Datapoint | `core:groups` | CO `@Links` |
| Trade → Kind-Trade | — | verschachteltes `Trade` |
| Trade → Device | Name-String am Device | `DeviceInstanceRef` |
| Area → Line → Segment → Device | — | Topology-Baum |
| Site → Building | `loc:hasBuilding` (`prj:Site` synthetisch) | nicht in ETS |

`prj:Site` nicht aus 0.xml ableiten; optional KIM-Wurzel.

## Technisch weglassen (unverändert)

Keys, Hashes, `LoadedImage`, APDU-Zähler, ProjectTraces-Payload, Zip-Signatur.
