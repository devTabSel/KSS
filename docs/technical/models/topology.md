# Topology

Nur knxproj (`A-*` / `L-*` / `S-*`), nicht im TTL. IA kodiert Area/Line/Device. GET Collection/Item nur `/api/kss` (`/areas`, `/lines`, `/segments`).

Device.segment_id und Location.default_line_id verweisen hierher. TTL setzt `segment_id` nicht (Preserve).

Tabellen: `areas`/`area_versions` (`address` 0–15), `lines`/`line_versions` (`medium_type_ets_id`), `segments`/`segment_versions`. Unique `(installation_id, ets_id)`.
