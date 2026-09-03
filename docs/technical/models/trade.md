# Trade

Kein 3API-Resource-Typ. Kategorie 3 aus knxproj `Trade_t`. TTL persistiert keine `T-n`. `mac:assignedTrade` ist ein Name auf dem Device (`device_versions.assigned_trade`), kein Join auf `trades`. `tag:lighting` ist kein Gewerk.

GET Collection/Item nur `/api/kss/trades` (`/api/v1/trades` → 404). `PATCH /api/kss/installations` mit knxproj upsertet `T-n` und `trade_devices`.

Identität: `installation_id` + `ets_id` (`T-n`). Version: `name` (Kollision erlaubt), number, comment, description, `completion_status`, `parent_trade_id`.

`trade_devices` ist temporal: PK `(trade_id, device_id, last_modified)`, FK auf `devices.id`, `linked`. Unlink = `linked=false`.
