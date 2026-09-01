# Installation

3API `installation` plus knxproj-Identität und knx_master-Katalog. Nicht nach `main` mergen ohne Freigabe.

## Tabellen

- `installations` — UUID, `ets_id` (`P-040E-0`), `project_guid` (TTL-Namespace), `knx_project_id`, `installation_index`, **`group_address_style`** (immutable: ThreeLevel/TwoLevel/Free).
- `installation_versions` — 3API-Attribute; **`completion_status`** statt `state`; `master_data_version`.
- `installation_subscriptions` — current-state, `subscription_id` ohne FK (Subscription-Entität fehlt).
- Katalog current-state, Unique `(installation_id, ets_id)`: DPT, DPST, **datafields** (3API), FunctionTypes, DatapointRoles, SpaceUsages, MediumTypes.

Titel: `ProjectInformation/@Name` / TTL `dct:title`. `prj:Site` ist nicht die Installation.

## Kategorie

| Spalte | Kat. |
| --- | --- |
| id, title, comment, contract_number, last_modified, project_installation_number, type_description | 1 (3API) |
| completion_status | 1 als 3API `state`, semantisch = CompletionStatus / `core:state` |
| ets_id, guid, style, master_data_version, Katalog | 3 |

Runtime-`value` auf datafields wird nicht persistiert. Manufacturers-Keys, MaskVersions-Interna, Languages: weggelassen.
