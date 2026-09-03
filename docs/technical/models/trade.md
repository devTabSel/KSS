# Trade

Kein 3API-Resource-Typ. Kategorie 3 aus knxproj `Trade_t`. Nicht im TTL (nur `mac:assignedTrade` als Name, nicht eindeutig). `tag:lighting` ist kein Gewerk.

GET Collection/Item nur `/api/kss/trades` (`/api/v1/trades` → 404). `PATCH /api/kss/installations` upsertet `T-n` und `trade_devices`.

Identität: `installation_id` + `ets_id` (`T-n`). Version: `name` (Kollision erlaubt), number, comment, description, `completion_status`, `parent_trade_id`.

`trade_devices` ist temporal: PK `(trade_id, device_id, last_modified)`, FK auf `devices.id`, `linked`. Unlink = `linked=false`.
