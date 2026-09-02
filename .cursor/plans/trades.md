# Trades

Zwei Quellen, zwei Persistenzwege, **kein automatischer Join**. Einordnung: [README](README.md). Ingest: [PATCH Installation exports](patch-installation-exports.md). Zeit: [Temporale Semantik](temporal-bus-semantics.md). Vertrag: [KSS and KNX 3rd Party API](kss-and-knx-3rd-party-api.md). Join-Fakten: Skill `knx-semantik`.

Paket-Reihenfolge: Installation → Location → Topology → Device → Datapoint → **Trade**. 3API hat **keinen** Resource-Typ `trade`. `assignedTrade` / `tag:operatesForTrade` in der OpenAPI sind Kategorie-2-Beispiele, keine Kategorie-1-Felder.

## Entscheidung

ETS-Gewerke (`Trade/@Id` → `T-n`, Hierarchie, `DeviceInstanceRef`) existieren nur im knxproj. Der Semantic Export hat keine Individuen `prj:T-*`.

Deshalb:

| Import | Was persistieren | Was **nicht** tun |
| --- | --- | --- |
| `.knxproj` | Tabellen `trades` / `trade_versions` / `trade_devices` (ETS-Baum + Device-Kante) | Keine Trade-Zeile aus einem TTL-String ableiten |
| `.ttl` | Am **Device** den String `mac:assignedTrade`; die gesetzten KIM-Tags `tag:operatesForTrade` (`tag:lighting`, …) am Subjekt, das sie trägt | Keinen ETS-Gewerkbaum synthetisieren; String nicht auf `T-n` joinen |

Zusammenführung von knxproj-Gewerk und TTL-Name/Tags ist **spätere Nutzerbearbeitung** der importierten Semantik, nicht Teil von Ingest oder Mapper.

## knxproj → ETS-Gewerkbaum

Nur dieser Import füllt die bestehende Trade-Persistenz.

- Identität: `(installation_id, ets_id)` mit `ets_id` = `T-n` (Suffix von `Trade/@Id`, z. B. `P-040E-0_T-46` → `T-46`).
- Version: `name` (`@Name`, Kollision erlaubt), `number`, `comment`, `description`, `completion_status`, `parent_trade_id`.
- `Puid` nur an der Identität, nie Join-Schlüssel.
- Device-Kante: `DeviceInstanceRef/@RefId` → `trade_devices` (temporal, `linked`). Geräte haben in der XML **kein** Trade-Attribut.

Parser: xknxproject liefert Trades noch nicht (Fork-Extra, **Representer**). HTTP-GET für Trade ist nicht 3API; unter `/api/kss` nur nach explizitem Vertrag.

knxproj schreibt **nicht** `mac:assignedTrade` auf die Device-Version. Die XML-Kante bleibt `trade_devices`.

## TTL → Name und Tags, ohne Trade-Identität

### `mac:assignedTrade` (Gewerk-Name)

Am Device (`core:Device`), DatatypeProperty, `xsd:string`, max. eines.

- IRI: `http://schema.knx.org/2020/ontology/mac#assignedTrade`
- Instanzen: WA53H10 z. B. `prj:DI-1` → `"BUS_DPS1280"`; test_A 5: zwei Devices `"Gewerk 1"` bei verschiedenen XML-`T-n`.
- Persistenz: **Device-Version**, Freitext, nullable, **kein FK** auf `trades.id`.
- Das heutige Schema-Verbot „keine Devicespalte `assigned_trade`“ gilt nur gegen eine **Join-Spalte** auf den ETS-Baum. Die TTL-Namensspalte ist etwas anderes; Feldname mit dem Nutzer abstimmen (nicht `assigned_trade` als FK-Lesart).

### `tag:operatesForTrade` (KIM-Trade-Tags)

Anwendungsdomäne, **kein** ETS-Gewerk. Klasse `tag:Trade`, Individuen `tag:lighting`, `tag:heating`, `tag:shading`, `tag:metering`, `tag:electrical`, `tag:accessControl`, `tag:alarming`, …

- IRI Property: `http://schema.knx.org/2023/en50090-6-2/tag#operatesForTrade`
- Ontologie-Domain: `core:Aspect` ∪ `core:Datapoint` (nicht `core:Device`). 3API-Beispiel liegt an **Function**.
- Forschungs-TTL: Assertionen `tag:operatesForTrade` / `a tag:Trade` stehen nur im eingebetteten Ontologie-Dump, nicht an `prj:`-Individuen. Fehlen im Korpus ≠ weglassen: sobald ein Export sie setzt, persistieren.

Persistenz: Tags **am Subjekt, das sie trägt** (Function, Datapoint/Aspect; Device nur, wenn der Export sie dort behauptet). Liste von CURIE/IRI (`tag:lighting`). Kein Join auf `trades`.

TTL-Import erzeugt **keine** Zeilen in `trades` / `trade_devices`.

## Kein Auto-Merge

`mac:assignedTrade` ist nicht eindeutig (test_A 5). `tag:lighting` ist nicht `Trade/@Name` und nicht `T-n`.

Gleiche `project_guid` aus knxproj und TTL bleibt **dieselbe Installation**. Die drei Fakten koexistieren:

1. ETS-Baum `T-n` + `trade_devices`
2. Device-String `mac:assignedTrade`
3. KIM-Tags `tag:operatesForTrade`

Ingest, Representer-Join und APIler-Mapper verknüpfen (2)/(3) nicht mit (1). Später: Nutzerbearbeitung (Zuordnung Name/Tags ↔ Gewerk, optionales KSS-only-Gewerk). UI/API dafür ist nicht Teil dieses Pakets.

## HTTP (später)

| Baum | Trade |
| --- | --- |
| `/api/v1` | kein Resource-Typ `trade`; `assignedTrade` nicht als Kategorie 1 ausgeben |
| `/api/kss` | optional `kss:` für ETS-Gewerk, Device-Name und Tags; Extra-Verben nur hier |

## Schema-Ist vs. Soll

Ist: `trades` / `trade_versions` / `trade_devices` existieren; Device hat bewusst **keine** Join-Spalte `assigned_trade`.

Soll (Feldliste mit Nutzer, dann **Modellierer**):

- knxproj-Tabellen unverändert für ETS-Gewerke
- Device-Version: TTL-Namensfeld (kein FK)
- Tag-Speicher am tragenden Subjekt (Function/Datapoint; Device nur bei Assertion)

Kein Schema-Change in diesem Plan-Schnitt.

## Orchestrierung

1. Fork-Keys Trades + `DeviceInstanceRef` — **Representer** (`xknxproject`)
2. knxproj-Mapper → `trades` / `trade_devices` — **APIler**
3. TTL-Fill: Device-Name + Tags, ohne Trade-Zeilen — **Representer**
4. Nutzer-Merge-API — eigener Schnitt nach diesem Paket
