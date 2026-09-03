# Paket-Mappings

Feldlisten und Join-Regeln je Paket. HTTP-Ist aus den Routern in `src/kss/main.py`.

Quellen-Reihenfolge und Join: Skill `knx-semantik`. Temporal: [temporal.md](../temporal.md).

| Paket | Datei | HTTP-Ist |
| --- | --- | --- |
| Installation | [installation.md](installation.md) | GET v1+kss; PATCH `.knxproj` / `.ttl` |
| Location (+ Function) | [location.md](location.md) | GET v1+kss |
| Topology | [topology.md](topology.md) | GET kss (areas/lines/segments) |
| Device | [device.md](device.md) | GET v1+kss; `kss:assignedTrade` nur kss |
| Datapoint | [datapoint.md](datapoint.md) | GET v1+kss; GroupRange nur kss |
| Trade | [trade.md](trade.md) | GET kss |
