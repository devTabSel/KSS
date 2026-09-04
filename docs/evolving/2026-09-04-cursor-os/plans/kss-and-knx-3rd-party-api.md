# KSS and KNX 3rd Party API

Verbindlicher Vertrag für `/api/v1` (offizielle KNX IoT 3rd Party API) und `/api/kss`
(dieselbe Ressource plus `kss:` und Extra-Verben). Skill `kss-api`, Agent **APIler**.
Schema-Delta: **Modellierer**. Parser-Keys/TTL/BUS: **Representer**. Orchestrierung: **KSS**.
Live-Doku: **Blubberer**.

Einordnung: [README](README.md). Ingest: [PATCH Installation exports](patch-installation-exports.md).
Feldlisten: [KSS Modellierung](kss-modellierung.md). Zeit: [Temporale Semantik](temporal-bus-semantics.md).
Clients: [HomeAssistant KNX Integration](homeassistant-knx-integration.md). Gewerke: [Trades](trades.md).

Normative JSON/OpenAPI: Workspace `public-projects/knx-iot-3rd-party-api-schema/schemas/`
(nicht `schemas-2020/`) und `knxiot_api_openapi.yaml`. **Kein** Edit dieser Dateien.

Großes Ziel: dieselbe Installation, dieselbe UUID, zwei URL-Bäume; Clients (HA und andere)
lesen KSS statt lokalem Parse.

Alle Agents arbeiten auf **dieses Soll** hin. Ist-GET (Identifier, leere `relationships`
weglassen) ist Übergang, nicht das Ziel.

## Status (Ist 2026-09-03)

Umgesetzt: dualer Mount, Pagination in `deps.py`, Flavor/`ExtraDep`, Installation GET+PATCH,
Master-Katalog-Persistenz, Location/Function GET (Collection/Item), Location/Function-Ingest
im selben PATCH, Topology-Ingest und GET nur unter `/api/kss` (keine 3API-Ressourcen),
Device GET Collection/Item (dualer Mount) und Device-Ingest (Identität + Version, `location_id`/`segment_id`),
Channel/Folder/CommObject-Ingest und GET nur unter `/api/kss` (`comm_object_datapoints` aus CO-`@Links`),
Datapoint GET Collection/Item (dualer Mount) plus GroupRange nur `/api/kss`; Ingest füllt
`function_datapoints` (`at_type` `["knx:FunctionPoint"]`). Trade-Ingest und GET nur
`/api/kss/trades` (kein 3API-Typ); `trade_devices` aus DeviceInstanceRef.
TTL-Ingest am selben PATCH (`ingest_ttl`, `prj:` vor Ontologie): dieselben Identitäten;
Device `kss:assignedTrade`; kein Topology/Trade-Baum aus Turtle. JSON-LD offen.

GET-Ist weicht vom Schema ab: die meisten `relationships` noch JSON:API-Identifier
`{ "data": { "type", "id" } }`; leere Relationen und fehlende Nested-Routen weggelassen;
Collection-Filter fehlen. **Ausnahme GET-Soll:** Function (`functionLocation`,
`functionDatapoints`), Location (`parentLocation`, `childLocations`, `locationFunctions`,
`locationDevices`), Device (`deviceLocation`, `deviceDatapoints`), Datapoint
(`datapointFunctions`, `datapointDevice`). Function `meta.@type` = `["core:ApplicationFunction"]`.
Location `at_type` = `["loc:" + SpaceType]`. Function `at_type` = `["knx:FunctionPoint"]` aus knxproj-GA; Datapoint (CO) ohne persistiertes `@type` bis Tag-Store.
Kein `GET /node`. Kein `/.well-known/knx`, kein OAuth, keine Runtime-Werte. Zeitreise: `GET /api/kss/{at}/…`, nicht `?at=`.

Nächster Modellschritt: erledigt (`datapoint_versions.at_type`). Befüllung und reichhaltige Synthese von `@type` (KIM-Klassen,
URNs, Custom) erst mit dem **Tag-Store**. Bis dahin darf GET `@type` weglassen oder nur
ableiten, was schon liegt (Location `loc:…`, Function Oberklasse).

Paket-Ingest knxproj bis Channel/Folder/CO liegt.
Device-Ingest (Identität + Version, `location_id`/`segment_id`) ist da; BUS-Indizes (`bus_pa_bindings`/`bus_ga_bindings`) liegen.
Datapoint-Ingest (GA/`GR-n`, `function_datapoints`) ist da; `comm_object_datapoints` aus knxproj-CO-Links liegt.
Trade-Ingest (`T-n`, `trade_devices`) ist da; TTL-Name/Tags ohne Auto-Join später.
3API-Oberfläche (Nested, Filter, Node, Item-Links) **erst nach Basic-GET für alle Entitäten**.

## Src-Layout (unverändert)

```
src/kss/api/
  deps.py            # page[number]=0, page[size]=65536 nur hier
  flavor.py          # bind_flavor → request.state.api_flavor; ExtraDep
  jsonapi.py         # extra=; Item-Serializer
  installations.py   # read_router + kss_router (PATCH)
  locations.py       # read_router
  functions.py       # read_router + kss_router (application-functions, group-range)
  topology.py        # kss_router (keine 3API)
  devices.py         # read_router
  datapoints.py      # read_router + kss_router (channel/folder, group-ranges)
  trades.py          # kss_router (keine 3API)
  channels.py        # kss_router (keine 3API)
  folders.py         # kss_router (keine 3API)
  <entity>.py        # analog, eine Datei je Entität; Nested-GETs in der Datei des Primärs
```

`main.py`: derselbe `read_router` unter `/api/v1` und `/api/kss`; `kss_router` nur `/api/kss`.

Verboten: `src/kss/api/v1/`, `src/kss/api/kss/`, Router-Factory, Pfadparameter `/api/{tree}`,
generisches CRUD-Framework, 3API-JSON-Schema ändern, Fake-401.

| Baum | Vertrag |
| --- | --- |
| `/api/v1` | nur spezifizierte 3API. Kategorie-1. Kein Datei-Ingest. |
| `/api/kss` | dieselben relativen Pfade und Verben plus `kss:` und Extra-Verben. Aktuell = `max(last_modified)`. |

PATCH unter `/api/v1` weder Runtime noch OpenAPI. Extra-Verben (Datei-Ingest) nur `kss_router`.

## Drei JSON-Schichten (nicht zwei)

Für projektbezogene Entitäten X ∈ {installation, location, function, device, datapoint, datafield, subscription, timeseries}:

| Schicht | Schema | HTTP |
| --- | --- | --- |
| Collection-Dokument | `XCollection.json` | Listen-GET: Pflicht `meta.collection` (`number`/`size`/`total`) auch leer, `data` = Array von `XItem` |
| Einzel-Dokument | `X.json` | Item-GET: `data` = ein `XItem` (oft nullable) |
| Resource | `XItem.json` | in beiden |

`XCollection.json` enthält **keine** Filter. Filter sind OpenAPI-Query-Parameter der Listen-Operation.
Pagination-Query `page[number]` / `page[size]` ebenfalls Request-seitig; die Antwort spiegelt sie in `meta.collection`.

Ausnahmen: `Node` ist Singleton (`GET /node`, `Node.json` / `NodeItem.json`, keine Collection).
`/sites` ist gefilterte Location-Liste (Wurzeln), kein `SiteItem`. Installation-Liste hat nur Pagination, keine drei Filter.

`data.type` ist das JSON:API-Enum (`location`, `function`, …). Das ist nicht `meta.@type`.

## Item: `relationships` = `links.related`

Soll gegen `XItem.json` + `relatedLinksMember.json` (Runtime-Beispiele der OpenAPI):

```yaml
relationships:
  functionLocation:
    links:
      related: /functions/{id}/location
  functionDatapoints:
    links:
      related: /functions/{id}/datapoints
```

Kein Resource-Identifier im Pflicht-Vertrag. Der Link ist ein zweiter GET, keine eingebettete Subquery.

| Kardinalität | Beispiel | Antwort |
| --- | --- | --- |
| to-one | `/functions/{id}/location`, `/locations/{id}/parentlocation`, `/devices/{id}/location` | `X.json` (LocationItem darf `null` sein) |
| to-many | `/functions/{id}/datapoints`, `/locations/{id}/childlocations`, `/locations/{id}/functions` | passende `YCollection` |

URIs nicht persistieren — Serializer aus Mount-Prefix (`/api/v1` bzw. `/api/kss`) + Ressourcen-UUID.

Prosa „leere Member weglassen“ gilt für **leere `attributes`-Keys**, nicht zum Streichen schema-pflichtiger Relationship-Keys. `Installation200` sagt ausdrücklich: ohne Relation `relationships` weglassen — das bleibt für Installation.

Nested-Routen in derselben Entitätsdatei wie der Primär (`functions.py` enthält `/functions/{id}/location` und `/functions/{id}/datapoints`). Leere Datapoint-Listen **vor** Datapoint-Ingest sind erlaubt.

Die Listen `childLocations` / `locationDevices` / `locationFunctions` / `deviceDatapoints` sind **keine** Tabellen ([KSS Modellierung](kss-modellierung.md)); GET leitet sie aus FKs und Kanten ab.

### Relationen — Inventar (APIler-Checkliste)

✅ = GET-Soll erledigt: Pflicht-/Optional-Key als `relatedLinksMember` **und** Nested-GET
(to-one: `X.json` mit `data` nullable + `meta.nodata`; to-many: `YCollection` inkl. leer `total: 0`).
JSON:API-Identifier ohne Nested zählt nicht. ⏭ = nicht bauen (Nutzer).

**Spec → HTTP:** `pflicht` und `optional` → `/api/v1` **und** `/api/kss`. `unspecced` → nur `/api/kss`.
BUS-Indizes haben keinen GET.

Nicht in der Tabelle: Versions-Identität (`*_versions.entity_id`); Besitz `installation_id`;
Katalog `master_data_id` / Translations. 3API-GET: `datapoint` = `comm_objects`, `function` = `group_addresses`.
ETS ApplicationFunction (`functions` / `F-n`) nur `/api/kss/application-functions`.

| | Primär | Relation | Kard. | Persistenz | Spec | HTTP |
| --- | --- | --- | --- | --- | --- | --- |
| ✅ | Function | `functionLocation` | 1 | abgeleitet: `function_group_addresses` → ETS-Function → `function_versions.location_id` | pflicht | v1+kss |
| ✅ | Function | `functionDatapoints` | n | `comm_object_group_addresses` (`linked`); Inverse von `datapointFunctions` | pflicht | v1+kss |
| ✅ | Location | `parentLocation` | 1 | `location_versions.parent_location_id` | pflicht | v1+kss |
| ✅ | Location | `childLocations` | n | abgeleitet: `parent_location_id` | pflicht | v1+kss |
| ✅ | Location | `locationFunctions` | n | abgeleitet: ETS-Function am Ort → `function_group_addresses` → GA | pflicht | v1+kss |
| ✅ | Location | `locationDevices` | n | abgeleitet: `device_versions.location_id` | optional | v1+kss |
| ⏭ | Location | `defaultLine` | 1 | `location_versions.default_line_id` | unspecced | kss |
| ✅ | Device | `deviceLocation` | 1 | `device_versions.location_id` | pflicht | v1+kss |
| ✅ | Device | `deviceDatapoints` | n | `comm_objects.device_id`; Inverse von `datapointDevice` | pflicht | v1+kss |
| ⏭ | Device | `segment` | 1 | `device_versions.segment_id` | unspecced | kss |
| ✅ | Datapoint | `datapointFunctions` | n | `comm_object_group_addresses` (`linked`); Inverse von `functionDatapoints` | pflicht | v1+kss |
| ✅ | Datapoint | `datapointDevice` | 1 | `comm_objects.device_id`; Inverse von `deviceDatapoints` | optional | v1+kss |
| ✅ | Function | `groupRange` | 1 | `group_address_versions.group_range_id` | unspecced | kss |
| ✅ | GroupRange | `parentGroupRange` | 1 | `group_range_versions.parent_group_range_id` | unspecced | kss |
| ✅ | GroupRange | `childGroupRanges` | n | abgeleitet: `parent_group_range_id` | unspecced | kss |
| ⏭ | Line | `area` | 1 | `line_versions.area_id` | unspecced | kss |
| ⏭ | Segment | `line` | 1 | `segment_versions.line_id` | unspecced | kss |
| ✅ | Trade | `parentTrade` | 1 | `trade_versions.parent_trade_id` | unspecced | kss |
| ✅ | Trade | `childTrades` | n | abgeleitet: `parent_trade_id` | unspecced | kss |
| ✅ | Trade | `tradeDevices` | n | `trade_devices` (`linked`) | unspecced | kss |
| ✅ | Channel | `device` | 1 | `device_channels.device_id` | unspecced | kss |
| ✅ | Channel | `parentDevice` | 1 | Tree-Parent ist Device (`parent_channel_id` NULL) | unspecced | kss |
| ✅ | Channel | `parentChannel` | 1 | `device_channel_versions.parent_channel_id` | unspecced | kss |
| ✅ | Channel | `parent` | 1 | Channel oder Device (direkt) | unspecced | kss |
| ✅ | Channel | `childChannels` | n | abgeleitet: `parent_channel_id` | unspecced | kss |
| ✅ | Channel | `childFolders` | n | abgeleitet: Folder.`parent_channel_id` | unspecced | kss |
| ✅ | Channel | `childDatapoints` | n | KO `channel_id`, ohne `folder_id` | unspecced | kss |
| ✅ | Channel | `children` | n | Channels + Folders + direkte Datapoints | unspecced | kss |
| ✅ | Folder | `device` | 1 | `device_folders.device_id` | unspecced | kss |
| ✅ | Folder | `parentDevice` | 1 | Tree-Parent ist Device (beide Parent-FKs NULL) | unspecced | kss |
| ✅ | Folder | `parentFolder` | 1 | `device_folder_versions.parent_folder_id` | unspecced | kss |
| ✅ | Folder | `childFolders` | n | abgeleitet: `parent_folder_id` | unspecced | kss |
| ✅ | Folder | `parentChannel` | 1 | `device_folder_versions.parent_channel_id` | unspecced | kss |
| ✅ | Folder | `parent` | 1 | Folder, Channel oder Device (direkt) | unspecced | kss |
| ✅ | Folder | `childDatapoints` | n | KO `folder_id` | unspecced | kss |
| ✅ | Folder | `children` | n | Folders + Datapoints | unspecced | kss |
| ✅ | Datapoint | `channel` | 1 | `comm_object_versions.channel_id` | unspecced | kss |
| ✅ | Datapoint | `folder` | 1 | `comm_object_versions.folder_id` | unspecced | kss |
| ✅ | Datapoint | `parentDevice` | 1 | Device nur ohne Channel/Folder | unspecced | kss |
| ✅ | Datapoint | `parent` | 1 | Folder, sonst Channel, sonst Device | unspecced | kss |
| ✅ | Datapoint | `children` | n | immer leer (Blatt) | unspecced | kss |
| ✅ | ApplicationFunction | `location` | 1 | `function_versions.location_id` | unspecced | kss |
| ✅ | ApplicationFunction | `functions` | n | `function_group_addresses` (`linked`) | unspecced | kss |
| | Installation | `installationSubscriptions` | n | `installation_subscriptions` (kein Subscription-Item) | optional | v1+kss |
| | BUS | PA→Device | n | `bus_pa_bindings.device_id` | unspecced | — |
| | BUS | GA+Device | n | `bus_ga_bindings` | unspecced | — |

3API-Relationen **ohne** Instanz-Zeile (Spec trotzdem, GET erst mit dem jeweiligen Paket):

| | Primär | Relation | Kard. | Persistenz | Spec | HTTP |
| --- | --- | --- | --- | --- | --- | --- |
| | Datapoint | `datapointProxy` | 1 | — (Runtime) | optional | v1+kss |
| | Datapoint | `datapointSubscriptions` | n | — (Subscription-Paket) | optional | v1+kss |
| | Datafield | `datafieldDatapoints` | n | Katalog `datafields`; keine Instanzkante | pflicht | v1+kss |
| | Node | `nodeSubscriptions` | n | — (Node synthetisch; Subscription-Paket) | optional | v1+kss |
| | Subscription | `subscriptionDatapoints` | n | — | optional | v1+kss |
| | Subscription | `subscriptionInstallations` | n | inverse `installation_subscriptions` | optional | v1+kss |
| | Subscription | `subscriptionNode` | 1 | — | optional | v1+kss |
| | Timeseries | `timeseriesDatapoint` | 1 | — (Runtime) | pflicht | v1+kss |

OpenAPI-Nested (nur Spec-Keys): `/functions/{id}/location`, `/functions/{id}/datapoints`,
`/locations/{id}/parentlocation`, `/childlocations`, `/functions`, `/devices`,
`/devices/{id}/location`, `/devices/{id}/datapoints`, `/datapoints/{id}/functions`,
`/device`, `/proxies`, `/subscriptions`.

## Collection-Filter (Request, nicht Collection-JSON)

**Später** (Nutzer 2026-09-03): Nested Parent/Child zuerst. Kein Filter-Parser in diesem Schnitt.

Wiederverwendete OpenAPI-Parameter an **Listen-GETs** (Top-Level und Nested), nicht an Item-GET:

- `filter[meta.@type][operator]` — Klassenname oder URN; Default-Operator `eq`; `or` kommagetrennt
- `filter[tagKey][operator]` — KIM-Tag-Individuen / OP-Pfad (`hasTag`, `hasLocationUsage`, …)
- `filter[attributeKey][operator]` — Kategorie-1-Attribute (`title`, `comment`, `state`, …)

`GET /installations`: nur `page[number]` / `page[size]`.
Proxies-Liste: Tag/Attribute, kein `typeFilter` (OpenAPI).
Unbekannter oder nicht berechenbarer Filter → **400/422**, nicht stillschweigend ignorieren (OpenAPI `tagFilter`).
Item-GET ignoriert Pagination-Query laut Spec.

Ein gemeinsamer Query-Parser (`request.query_params`, Klammer-Syntax). FastAPI-`Query`-Namen allein reichen nicht.

| Filter | Wann |
| --- | --- |
| `@type` | sobald `at_type` bzw. Synthese Werte hat |
| `title` / `comment` / `description` / `state` | sobald die Collection existiert |
| `hasLocationUsage` | Location `usage` |
| voller KIM-`tagFilter` | **Tag-Store** |
| `filter[value]` | Runtime / Bus |
| Vendor-Keys (`gira:…`) | **nicht**. Höchstens ganz zuletzt, nur auf aus `.knxproj`/`.ttl` importierte Vendor-Daten, falls überhaupt abbildbar |

Custom Tags und Custom Entities (Anwender deklariert, Werte temporal über OpenAPI-Queries fixieren) gehören in den Tag-Store, nicht in `additionalProperties` der 3API.

## `meta.@type` vs Tags vs `data.type`

| | Persistenz | 3API | Filter |
| --- | --- | --- | --- |
| JSON:API-Typ | nicht | `data.type` Enum | — |
| Ontologieklasse | `*_versions.at_type` ARRAY | `meta.@type` | `filter[meta.@type]` |
| Tag-Individuen | `usage`, später Tag-Store | nicht als `@type` | `tagFilter` |
| ETS-Token | `location_type`, `function_type_ets_id`, `datapoint_subtype_ets_id` | unter `/api/v1` nicht als diese Namen; `/api/kss` `kss:` | `attributeFilter` nur wo Kategorie-1 |

`meta.@type` ist JSON-LD-Klassenzugehörigkeit (0..n IRIs/CURIEs/URNs). Spec-Beispiele: Location `loc:Room` + `urn:knx:loc.room`; Function `knx:switching` + `urn:knx:fct.switching` (+ Hersteller); Datapoint `knx:dpa.417.61` / `knx:FunctionPoint`; Device `core:Device` / `td:Thing`. `typedescription` ist nur Doku-URL, optional, nicht persistieren (synthetisch erlaubt).

Installation hat im Item-Schema **kein** `@type` — keine Spalte (Plan Modellierung bestätigt).

Ist-Synthese bis Tag-Store:

- Location: `["loc:" + location_type]` wenn Type gesetzt
- Function: `["core:ApplicationFunction"]` (Oberklasse; spezifische `fct.*` später)
- Device: Spalte vorhanden, Fill mit Device-Paket / später Store
- Datapoint: Spalte **anlegen**, Fill später (Store und/oder Ableitung `knx:FunctionPoint` + DPST/`dpa.*` aus KIM)

Tag-Store setzt oder synthetisiert `@type` (GET-Zeit oder persistierte Array-Version). Ingest darf schmale Defaults lassen. `at_type` nicht mit der gedroppten `datapoint_versions.datapoint_type` verwechseln (das war ein Attribut-Array).

## Node — synthetisieren, nicht aus knxproj

Node = **dieser KSS-Prozess** (3API-Server), eine Instanz, nicht Installation, nicht ETS-Gerät.

`GET /node` → `Node.json`. `data.type` = `service` (KSS ist Dienst; `device` nur wenn später eine Box das so deklariert). `data.id` = stabile UUID aus **Konfiguration** (nicht ETS, nicht pro Request neu).

Pflichtattribute synthetisch:

- `title`, `deviceOrServiceName`, `vendorOrProvider` (`kss` als Provider-Name für spätere `kss:`-Keys)
- `maxSubscriptions` / `currentSubscriptions` — bis Subscription-Paket: Maximum aus Config, current `0`
- `currentDateTime` — Prozessuhr UTC
- `version.server` — KSS-Release
- `lastModified` — letzte Node-Config-Änderung oder weglassen wenn unbekannt
- `relationships.nodeSubscriptions` erst mit Subscriptions; OpenAPI-Pfade `/subscriptions` bevorzugen gegenüber Beispiel `/node/subscriptions`

Kein `nodes`-Table. `/.well-known/knx` und OAuth **nach** Runtime/Messaging (Entdeckung/Auth). Minimales `GET /node` darf früher existieren (statisch + Uhr + Zähler 0).

## Reihenfolge der 3API-Fähigkeiten (nicht Ingest-Pakete)

1. **GET-Soll** Nested: `links.related` + Parent/Child auf derselben Primärressource. Collection-Filter **danach**.
2. Ingest-Pakete Topology → Device → Datapoint → Trade; Device/Datapoint-GET analog Item-Soll; `function_datapoints` füllt Nested.
3. **`GET /node`** synthetisch, sobald sinnvoll (unabhängig vom nächsten Ingest-Paket).
4. **Tag-Store** (eigenes Modell, Nutzer): Custom Tags/Entities, temporale Werte per OpenAPI-Query; speist `tagFilter` und `@type`-Synthese.
5. **Runtime** mit Bus-Anbindung: Datapoint `value`/`timestamp`, `filter[value]`, Timeseries. Werte nicht in MaC-Versionstabellen (Lücke in `datapoint.py` bleibt bis Runtime-Paket).
6. **Auth / Messaging** nach Runtime: OAuth2, `/.well-known/knx`, WebSocket, HTTP-Callbacks. Keine Fake-401 vorher.
7. Subscription-Entität (FK von `installation_subscriptions`). Proxy nur wenn Semantik aus Import/Runtime existiert.
8. Vendor-`attributeFilter` höchstens zuletzt, nur importierte Vendor-Daten.

`datapointProxy` / `currentDateTime` am **Device** (Geräteuhr) sind Runtime/IoT, nicht MaC. Device-`currentDateTime` in Spec-Beispielen nicht aus knxproj füllen.

## Rollen — jeder Agent setzt diesen Plan um

**KSS:** Orchestriert auf dieses Soll, nicht auf das GET-Ist. Nächste parallele Schnitte: APIler Nested+Links+Filter und/oder synthetisches Node; knxproj-Ingest bis Trade liegt. Skill `kss-api` und dieser Plan vor jedem HTTP-Auftrag.

**Modellierer:** `data`/`meta`/`relationships` nicht als Tabellen. Relationships = FKs/Kanten. `at_type` ARRAY an Location/Function/Device/Datapoint-Versionen; Installation ohne `@type`. Datapoint-`at_type` liegt (008). Tag-Store später eigenes Paket (Feldliste mit Nutzer). Runtime-Werte/Timeseries/Subscriptions eigene Pakete, nicht in `datapoint_versions`. Keine Vendor-EAV für 3API-`additionalProperties`. Node nicht modellieren.

**APIler:** `/api/v1` nur OpenAPI-Pfade. Serializer auf `relatedLinksMember`. Nested-Routen anlegen. Filter-Parser einmal. Node synthetisch, kein Ingest. `kss:` nur bei `extra`. Kategorie-1 unter v1. GET-Soll dieses Plans gilt vor dem älteren Satz „leere relationships weglassen“ (gilt weiter nur für Installation und für leere Attribute). Tests gegen WA53H10 / Fixtures anpassen, wenn GET-Soll umgestellt wird.

**Representer:** Fork liefert Tokens (`FT-*`, `DPST-*`, Space Type, Usage), nicht fertige KIM-IRIs. `@type`-Reichtum kommt Tag-Store/KIM-Join (TTL `rdf:type`), nicht durch Umschlüsselung Name/IA. BUS-Fill ermöglicht später Runtime, nicht Node.

**Blubberer:** Nach Ist-Änderung fachlich/technical: Collection vs Item, `links.related`, Filter in der OpenAPI nicht im Collection-JSON, Node synthetisch, `@type` vs Tags. Ist-GET erst als Soll beschreiben, wenn der Code umgestellt ist.

## Nicht tun

- 3API-JSON/OpenAPI ändern
- parallele `api/v1/` / `api/kss/`-Pakete
- OAuth/Fake-401 vor dem Auth-Schnitt
- Node aus Installation oder knxproj ableiten
- `meta.@type` mit Tags oder `data.type` zusammenwerfen
- `datapoint_type`-ARRAY wiederbeleben statt `at_type`
- Vendor-Filter vor Tag-Store/Runtime erfinden
- URLs von `links.related` in der DB speichern
- generisches Resource/CRUD-Framework
- `/api/{tree}/…` als Pfadparameter
