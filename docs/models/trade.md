# Trade

Kein 3API-Resource-Typ. Kategorie 3 aus knxproj `Trade_t`. Nicht im TTL (nur `mac:assignedTrade` als **Name**, nicht eindeutig). `tag:lighting` ist kein Gewerk.

Identität: `installation_id` + `ets_id` (`T-n`). Version: `name` (Kollision erlaubt), number, comment, description, `completion_status`, `parent_trade_id`.

`trade_devices` ist **temporal**: PK `(trade_id, device_id, _since)`, FK auf `devices.id`, `linked`. Unlink = `linked=false`.
