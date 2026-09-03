# Persistenz

Eine Alembic-Kette, eine `temporal.py`. Function ist kein eigenes Paket.

## Pakete

```
Installation  Identität + Version + Subscriptions (current-state) + knx_master / datafields
Location      Spaces + ApplicationFunction + function_datapoints (temporal)
Topology      Area / Line / Segment
Device        3API Device + Channel / Folder / CommObject + comm_object_datapoints; Produkt/Hersteller-XML global (`master_products`, …)
Datapoint     GroupAddress (= 3API datapoint) + GroupRange
Trade         Gewerke + trade_devices (temporal)
```

Bewusste Lücken: Timeseries, Subscription-Resource, Node, Datapoint-Runtime `value`/`timestamp`, `datapointProxy`.

## Regeln

- Identitätstabelle (3API-UUID) + Version PK `(entity_id, last_modified)`. Import-Uhr: `installations.last_import`. Mixin: `src/kss/models/temporal.py`.
- Kein `valid_to`, kein GiST-Exclude, kein Surrogat auf Versionen.
- `ets_id` lokal (`DI-1`), Unique `(installation_id, ets_id)` bzw. `(device_id, ets_id)` für geräteinterne Objekte.
- Hersteller-XML-Katalog global Unique `knx_id` (kein `installation_id`, kein `master_data_id`).
- `puid` XML-only, optional auf der Identität.
- snake_case; JSON:API-Hüllen nicht persistiert.
- Kanten N:M temporal; Unlink = neue Zeile `linked=false`.
- semantisch gleiche Namen (3API / KIM / knxproj) = **eine** Spalte.
- Kategorie 1 = 3API-Ausgabe; Kategorie 3 = KIM/knxproj ohne 3API (`kss:` unter `/api/kss`).

## Alembic

Lineare Kette: `001_unified` → `002_installation_project_attrs` → `003_temporal_lm_bus` → … → `011_manufacturer_xml_catalogs`.

`003` ist Migration (DDL-History). Leser-Doku verwendet `last_modified` / `last_import`, nicht die alten Spaltennamen als Ist. `011` legt die globalen Hersteller-XML-Tabellen an und nimmt `order_number`/`manufacturer` von `device_versions`.

## Src

`src/kss/models/` — eine Datei je Paket plus `temporal.py` / `base.py`. Details: [models/](models/README.md).
