# 2026-09-03 — TTL Semantic Export ingest

Ist aus Code: `kss.services.ttl` (`parse_ttl` / `ingest_ttl`), `PATCH /api/kss/installations` für `.ttl` (201/204, 422 bei Müll), Join `project_guid` + `ets_id`. Device `assigned_trade` aus `mac:assignedTrade`; GET `kss:assignedTrade` / `kss:operatesForTrade` nur `/api/kss`.

Live-Docs sagten vorher 501 / „TTL geplant“ / „HTTP nur Installation“ / „assigned_trade gibt es nicht“. Archiv: `docs/evolving/2026-09-03-ttl-ingest/`.

Bewusst weiter Lücke: JSON-LD, TTL ohne Topology/Trades/Channels/BUS/GroupRange, kein Auto-Join auf `trades.T-n`.
