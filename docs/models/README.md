# Vereinheitlichtes Persistenzmodell

Branch/Worktree `KSS-DB-model`, Basis `main` (`b58d751`). **Nicht nach `main` mergen** ohne explizite Freigabe.

Die fünf unabhängigen 3API-Pakete (`KSS-DB-model-installation` … `-trade`) bleiben als Historie stehen. Dieses Worktree ersetzt sie fachlich durch **eine** Alembic-Kette und verdrahtete Fremdschlüssel. Function ist kein eigenes Paket mehr.

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
| `trade_devices` current-state | temporal, PK `(trade_id, device_id, _since)`, `linked` |
| Device-Beispiel `assignedTrade` | keine Devicespalte; Kante `trade_devices` |

## Gemeinsame Regeln

- Identitätstabelle (3API-UUID) + Version PK `(entity_id, _since)` + `_observable_since`.
- Kein `valid_to`, kein GiST-Exclude, kein Surrogat auf Versionen.
- `ets_id` lokal (`DI-1`), Unique `(installation_id, ets_id)` bzw. `(device_id, ets_id)` für geräteinterne Objekte. Vollständige knxproj-Id ist rekonstruierbar.
- `puid` XML-only, optional auf der Identität.
- snake_case; JSON:API-Hüllen nicht persistiert.
- Kanten N:M temporal; Unlink = neue Zeile `linked=false`.

Details je Paket in den Dateien dieses Ordners. Import-Regeln: Skill `knx-import` (Agent `importer` implementiert noch nichts).
