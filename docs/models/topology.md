# Topology

Nur knxproj (`A-*` / `L-*` / `S-*`), nicht im TTL. IA kodiert Area/Line/Device.

Device.segment_id und Location.default_line_id verweisen hierher.

Tabellen: `areas`/`area_versions` (`address` 0–15), `lines`/`line_versions` (`medium_type_ets_id`), `segments`/`segment_versions`. Unique `(installation_id, ets_id)`.
