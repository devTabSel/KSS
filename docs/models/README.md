# Vereinheitlichtes Persistenzmodell

Eine Alembic-Kette auf `main`, verdrahtete Fremdschlüssel. Function ist kein eigenes Paket.

## Pakete

```
Installation  Identity + Version + Subscriptions (current-state) + knx_master-Katalog/datafields
Location      Spaces + ApplicationFunction + function_datapoints (temporal)
Topology      Area / Line / Segment
Device        3API Device + Channel / Folder / CommObject + comm_object_datapoints
Datapoint     GroupAddress (= 3API datapoint) + GroupRange
Trade         Gewerke + trade_devices (temporal)
```

Nicht modelliert (bewusst Lücken): Timeseries, Subscription-Resource, Node, Datapoint-Runtime `value`/`timestamp`, `datapointProxy`.

## Überlappungen, die hier aufgelöst sind

| Vorher | Jetzt |
| --- | --- |
| Fünf Kopien `temporal.py` / `base.py` | eine Kopie, Naming-Convention aus dem Installation-Paket |
| Fünf `001_*` mit `down_revision = None` | eine lineare Migration `001_unified` |
| `location_id` / `device_id` ohne FK | FK `ON DELETE RESTRICT` auf Identitäten |
| Function-Paket neben Location | Function im Location-Paket |
| Installation `state` vs Trade `completion_status` | überall `completion_status` (3API `state` = CompletionStatus = `core:state`) |
| `trade_devices` current-state | temporal, PK `(trade_id, device_id, last_modified)`, `linked` |
| Device-Beispiel `assignedTrade` | keine Devicespalte; Kante `trade_devices` |

## Gemeinsame Regeln

- Identitätstabelle (3API-UUID) + Version PK `(entity_id, last_modified)`. Import-Uhr: `installations.last_import`. Regeln: `src/kss/models/temporal.py`, `plans/temporal-bus-semantics.md`. BUS: `bus_pa_bindings`, `bus_ga_bindings`.
- Kein `valid_to`, kein GiST-Exclude, kein Surrogat auf Versionen.
- `ets_id` lokal (`DI-1`), Unique `(installation_id, ets_id)` bzw. `(device_id, ets_id)` für geräteinterne Objekte. Vollständige knxproj-Id ist rekonstruierbar.
- `puid` XML-only, optional auf der Identität.
- snake_case; JSON:API-Hüllen nicht persistiert.
- Kanten N:M temporal; Unlink = neue Zeile `linked=false`.

Details je Paket in den Dateien dieses Ordners. Import-Regeln: Skill `knx-import` (Agent `importer` implementiert noch nichts).
