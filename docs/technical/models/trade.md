# Trade

Kein 3API-Resource-Typ. Kategorie 3 aus knxproj `Trade_t` und aus TTL `prj:T-*`. `mac:assignedTrade` ist ein Name auf dem Device (`device_versions.assigned_trade`), kein Join auf `trades`. `tag:lighting` ist kein Gewerk.

GET Collection/Item nur `/api/kss/trades` (`/api/v1/trades` → 404). `PATCH /api/kss/installations` mit knxproj upsertet `T-n` und `trade_devices`. TTL persistiert `prj:T-*` und `knx:hasDevice` → `trades` / `trade_devices`. ETS Semantic Export hat typischerweise keine `prj:T-*` → 0 Trades (`tests/test_ttl.py`). KSS-TTL enthält `prj:T-*` und roundtrippt.

Identität: `installation_id` + `ets_id` (`T-n`). Version: `name` (Kollision erlaubt), number, comment, description, `completion_status`, `parent_trade_id`.

`trade_devices` ist temporal: PK `(trade_id, device_id, last_modified)`, FK auf `devices.id`, `linked`. Unlink = `linked=false`.
