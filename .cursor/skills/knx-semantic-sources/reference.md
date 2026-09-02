# TTL ↔ knxproj (Beispiel `test_A 5`, ETS 6.4.8718, Schema 23)

Quellen: `research/test_A 5 … Test_B.ttl` und entpackte `P-0260/0.xml`.
TTL-Präfix: `prj: <http://iot.knx.org/{ProjectInformation/@Guid}#>`
(`Guid="d0eb6c35-7a1e-41dd-8832-105ae1964af1"`).

## Join-Schlüssel

knxproj `@Id` = `P-0260-0_DI-2`. TTL-Subject = **`prj:DI-2`** (Objekttyp + Index, ohne `P-<ProjectId>-<InstallationIndex>_`).

Gleiches Muster: `BP-5`, `GA-2`, `T-2` (Trades **nicht** als TTL-Individuen in diesem Export). Installation: `prj:P-0260-0` = ProjectId + InstallationIndex.

`Puid` steht nur in der XML.

## `core:state` = CompletionStatus

In diesem Export überall `core:state "Undefined"` an Device, Location, Installation. In der XML fehlt `@CompletionStatus` → XSD-Default `Undefined`. Wert und Enum stimmen überein. Sentinel `core:state "Unknown"` nur am synthetischen `prj:Site` (nicht in `0.xml`).

## `tag:lighting` ≠ Gewerk

`tag:lighting` ist ein KIM-**Trade-Tag** (Anwendungsdomäne). ETS-Gewerke sind Projektinstanzen `Trade/@Id` / `@Name`. 3API hat **keinen** Resource-Typ `trade`. OpenAPI `assignedTrade` / `tag:operatesForTrade` sind Kategorie-2-Beispiele.

In **diesem** TTL: `mac:assignedTrade "Gewerk 2"` = **Name-String** des XML-Gewerks, keine Tag-IRI. Zwei XML-Gewerke heißen beide `"Gewerk 1"` (`T-3`, `T-4`) — der Name ist **nicht eindeutig**. Persistenz: Trade-Identität über `ets_id` (`T-3`), Zuordnung Device→Trade über `DeviceInstanceRef`, TTL-String nur als Anzeigename.

## Was der Semantic Export **nicht** enthält (nur knxproj)

- Topologie-Individuen `A-` / `L-` / `S-` (IA kodiert Area/Line/Device: `"1002"` = hex 1.0.2)
- Trade-Individuen `T-` (nur `mac:assignedTrade` am Device)
- Function `F-` (in diesem Projekt keine Functions)
- `CommunicationPartLoaded` / andere `*Loaded` (kein Download → `core:lastDownloaded` = `0001-01-01T00:00:00`)
- Leeres Device-`@Name`: TTL `dct:title` fällt auf **Produktnamen** zurück

## Gemeinsame Semantik (Felder, 3API egal)

Nur was in **beiden** Formaten vorkommt oder klar aufeinander abbildbar ist.

### Installation

| Feld | TTL | knxproj |
| --- | --- | --- |
| Join | `prj:P-0260-0` | `Project/@Id` + Installation (`P-0260` + `-0`) |
| Titel | `dct:title` "test_A" | `ProjectInformation/@Name` |
| lastModified | `core:lastModified` | `ProjectInformation/@LastModified` (identischer Timestamp) |
| state | `core:state` | `@CompletionStatus` (Default Undefined) |

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
| Individualadresse | `knx:individualAddress` hex-String `"1002"` | Area.`@Address` + Line.`@Address` + Device.`@Address` |
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
| Datapoint-Titel | `dct:title` "BASE_Heartbeat" | Katalog / CO (nicht Instanz-Attribut) |
| Flags | `core:readable`/`writable`, `mac:configFlags` "CRT" | CO-Flags (hier nicht in 0.xml überschrieben) |
| GA gruppiert CO | `core:groups` | `ComObjectInstanceRef/@Links="GA-2"` |

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

**Neu programmieren:** Auf dem Bus steht die 16-Bit-Adresse plus die Associationstabelle (KO↔GA), nicht der ETS-Name. Namensänderung an Range/GA braucht kein Device-Download. Änderung von `group_address` oder der Kante `comm_object_datapoints` schon: ETS setzt i. d. R. `CommunicationPartLoaded=false`, bis der Communication-Part geladen ist (`LastDownload`). `_since`-Zuweisung: `kss.models.temporal`. Bus-wirksam am Device ist die Extra-Version mit echtem `LastDownload`; `INITIAL_SINCE` und `communication_part_loaded=false` sind Annahmen.

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

**Download-Semantik für `_since`:** siehe `kss.models.temporal`. `CommunicationPartLoaded` nur XML. Extra-Device-Version mit `_since = LastDownload` nur bei Flag **und** echtem Datum; `core:lastDownloaded` MinDate allein reicht nicht.

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
