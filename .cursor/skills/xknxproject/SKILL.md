---
name: xknxproject
description: >-
  Additive xknxproject fork (devTabSel/xknxproject): origin
  github.com/devTabSel/xknxproject, upstream github.com/XKNX/xknxproject.
  One parse(combine=True default); KSS uses parse(combine=False). Extra info
  keys, ets_id on objects, GitHub fork/PR/rebase. Use when changing the
  parser, ProjectInfo, XML loader, combine_project, stubs, or when the user
  mentions XKNX, xknxproject, upstream, fork remotes, or HA knxproj parse.
  Do not use for KSS REST, Alembic, or TTL import.
---

# xknxproject

## Mandatory delegation

`Representer` is the sole executor of fork edits.

**APIler** must read this entire skill (same knowledge as Representer) but must not change the fork. Fork work: delegate to `Representer`.

When this skill is invoked for parser/fork changes:

1. Do NOT perform the fork work in the current agent.
2. Delegate the complete task to the `Representer` subagent.
3. `Representer` must read and follow this entire skill.
4. Return the result of the `Representer` execution to the user.

Regelwerk für Agent **Representer** (Parser-Fork). **APIler** liest denselben Text. Checkout: `devTabSel/xknxproject`. KSS konsumiert den Dict in `kss/services/knxproj.py` (`parse(combine=False)`). TTL/Join/BUS: Representer, Skill `knx-semantik`, nicht dieser Skill. Unklar → Nutzer fragen.

## Ziel

Ein Parser für ETS-Projekte, den Home Assistant unverändert (`combine=True`) und KSS roh (`combine=False`) nutzen kann. Extra-Felder nur **additiv**, damit Upstream-PRs nach [XKNX/xknxproject](https://github.com/XKNX/xknxproject) möglich bleiben. Großes Ziel: [Pläne-README](../../plans/README.md).

## Pläne

- [README](../../plans/README.md)
- [PATCH Installation exports](../../plans/patch-installation-exports.md)
- [KSS and KNX 3rd Party API](../../plans/kss-and-knx-3rd-party-api.md)
- [Temporale Semantik](../../plans/temporal-bus-semantics.md)
- [HomeAssistant KNX Integration](../../plans/homeassistant-knx-integration.md)

## Remotes

| Remote | URL |
| --- | --- |
| `origin` | `https://github.com/devTabSel/xknxproject.git` |
| `upstream` | `https://github.com/XKNX/xknxproject.git` |

Lokal arbeiten im Fork-Checkout, nicht im KSS-Repo. `gh` für Issues/PRs/Checks gegen origin bzw. Upstream-PRs nach `XKNX/xknxproject`.

## API (unverhandelbar)

```python
def parse(self, combine: bool = True) -> KNXProject
```

- Kein `parse_kss()`, keine zweite TypedDict-API.
- `combine=True` (Default): bisheriges HA-Verhalten (`combine_project`).
- `combine=False`: rohes ETS — das nutzt KSS.
- Bestehende Dict-Keys und Werte bleiben. Zusätzliche Keys dürfen dazukommen.
- Extra `info`-Keys immer füllen (billig), nicht hinter einem Flag.

Typen: `xknxproject/models/knxproject.py`. Einstieg: `xknxproject/xknxproj.py`. XML: `xknxproject/xml/parser.py`, Loader unter `xknxproject/loader/`.

## `info` (Stand Installation)

Bereits upstream-ähnlich: `project_id`, `name`, `last_modified`, `group_address_style`, `guid`, `created_by`, `schema_version`, `tool_version`, `xknxproject_version`, `language_code`.

KSS-additiv (bereits im Fork): `installation_index`, `ets_id`, `completion_status` (XML-Omit → `Undefined`), `comment`, `master_data_version`, `project_number`, `contract_number`, `project_type` (XML-Token, z. B. `Family House`), `project_start` (`ProjectInformation/@ProjectStart`, ISO-String wie in XML), `bcu_key` (`Installation/@BCUKey` in `0.xml`), `ip_routing_backbone_key` (`Installation/@IPRoutingBackboneKey` in `0.xml`). Leer/Omit → `null`. Keine IP-Latenzen, BusAccess, Hashes, ToDos, LastUsedPuid, ArchivedVersion.

Sprachlabels (`Familienhaus`) nicht erfinden. Schema **≥ 23** lehnt KSS ab, der Parser darf ältere Projekte weiter lesen.

## `locations` / Space (additiv, Dict weiter nach Name)

`locations` bleibt nach **Name** geschlüsselt (`_recursive_convert_spaces`). Additive Keys auf jedem Space, immer:

| key | Quelle | Leer/Omit |
| --- | --- | --- |
| `ets_id` | Suffix von `@Id` nach dem letzten `_` (`P-040E-0_BP-1` → `BP-1`) | immer, Pflicht |
| `comment` | `@Comment` | `null` |
| `completion_status` | `@CompletionStatus` | `null` (kein `Undefined` erfinden; Space-Omit ist üblich) |
| `last_modified` | `@LastModified` | `null` (KSS fällt auf Project-LastModified zurück) |
| `default_line` | Suffix von `@DefaultLine` (`P-040E-0_L-5` → `L-5`) | `null` |

Bestehend bleibt: `identifier` (volle Id), `usage_id` (roh `@Usage`, auch `tag:`), `usage_text`, `type`, `name`, `number`, `description`, nested `spaces`, `functions`, `devices` (weiter IA).

## `functions` / Function (additiv)

`parse_functions` setzt `identifier` weiter auf Suffix `F-n`. Additive Keys, immer:

| key | Quelle |
| --- | --- |
| `ets_id` | gleich `identifier` (`F-n`), auch wenn redundant |
| `description` | `@Description`, leer → `null` |
| `comment` | `@Comment`, leer → `null` |
| `completion_status` | `@CompletionStatus`, omit → `null` |
| `last_modified` | `@LastModified`, omit → `null` |

Bestehend: `function_type`, `space_id` (volle Space-Id), `group_addresses`, `usage_text`.

Leere XML-Strings → `None` via `_optional_xml_str`. HA-Stubs: `assert_stub` erlaubt extra Keys auf `locations`/`functions` und nested `spaces` (wie bei `info`); Stub-JSON muss die neuen Keys nicht listen.

## `master_data` (`combine=False` only)

`parse(combine=False)` hängt den Top-Level-Key **`master_data`** an: knx_master-Katalog (DPT/DPST, datafields, FunctionTypes, Roles, SpaceUsages `SU-*`, MediumTypes, FunctionPoints, Manufacturers) plus **`translations`** für alle Sprachen außer en-US. Inline `@Text`/`@Name` auf den Entities ist der en-US-Default; `language=` overlayt diesen Katalog **nicht**. Default `parse()` / `parse(combine=True)` hat **kein** `master_data` (HA-Pfad bleibt billig, keine Languages-Walk).

## Nicht umschlüsseln

Bekannte Upstream-Lücken — KSS darf sie nicht „wegfixen“ durch andere Keys:

- Locations nach **Name** (`_recursive_convert_spaces`; test_A: doppelte „Raum 1“)
- Devices nach **Individualadresse**
- GroupRanges ohne `GR-n` / `Id`
- unlinked COs verwerfen

Stattdessen **additive** Keys (`ets_id`, Identifier behalten). Details: [reference.md](reference.md). Keine fertigen KIM-IRIs / `meta.@type` im Parser — Tokens (`FT-*`, `DPST-*`, Space Type, Usage); Synthese in KSS (Tag-Store). [3API-Plan](../../plans/kss-and-knx-3rd-party-api.md).

## GitHub / Fork

1. Vor Parser-Arbeit: `git fetch upstream` und Stand relativ zu `upstream/main` kennen.
2. Additive Commits auf einem Fork-Branch; Default `combine` und Stub-JSON für bestehende Tests nicht brechen.
3. Tests im Fork (`test/`, Stubs unter `test/resources/stubs/`). KSS-XSD-Korpus: alle `research/*.knxproj` (WA53H10 produktiv; `test_A*` Reverse Engineering, z. B. doppelte „Raum 1“). TTL: alle `research/*.ttl`, Skill `knx-semantik`, nicht in den Fork.
4. Upstream-PR nur für Änderungen, die XKNX nützen (keine KSS-only-Hacks, keine Persistenz).
5. `gh pr create` / `gh pr view` / Checks. Kein force-push auf `main`. Kein `git config` ändern.
6. Andere [XKNX](https://github.com/XKNX/)-Repos (`xknx`, `knx-integration`, `knx-frontend`) nicht anfassen, bis der Nutzer das verlangt.

## Nicht tun

- KSS-REST, Alembic (TTL/Join/BUS: Representer mit Skill `knx-semantik`, nicht hier)
- Locations/Devices umschlüsseln
- `combine`-Default ändern
- Eigenparser in KSS
