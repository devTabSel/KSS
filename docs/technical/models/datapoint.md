# Datapoint

3API `datapoint` = knxproj `GroupAddress` = TTL `knx:FunctionPoint`. CommObjects sind das nicht. HTTP noch nicht verdrahtet.

## Identität vs. Busnummer

`ets_id` `GA-n` und `puid` bleiben, wenn nur `@Address` geändert wird. Neue Version, gleiche `datapoint_id`. Löschen+Anlegen = neue Id. Semantik hängt an `datapoint_id`.

`group_address` ist Integer 0…65535. Keine Haupt-/Mittelgruppe-Spalten. Anzeige aus `installations.group_address_style`.

## GroupRange

`GR-*`, nur knxproj, temporal (Name, Parent, `range_start`/`range_end`). `group_range_id` auf der Datapoint-Version (Umhängen historisiert).

## Nicht hier

`value`, `timestamp` (Runtime-Lücke). Enum/Unit/Min/Max → `datafields`. `datapointProxy` nicht modelliert.

Telegramm zur Zeit x: Installation + 16-Bit-Ziel + bus-wirksame Bindings. ETS-Semantik: `E(entity, x)`.
