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

KSS-additiv (bereits im Fork): `installation_index`, `ets_id`, `completion_status` (XML-Omit → `Undefined`), `comment`, `master_data_version`, `project_number`, `contract_number`, `project_type` (XML-Token, z. B. `Family House`). Leer/Omit → `null`.

Sprachlabels (`Familienhaus`) nicht erfinden. Schema **≥ 23** lehnt KSS ab, der Parser darf ältere Projekte weiter lesen.

## Nicht umschlüsseln

Bekannte Upstream-Lücken — KSS darf sie nicht „wegfixen“ durch andere Keys:

- Locations nach **Name** (`_recursive_convert_spaces`; test_A: doppelte „Raum 1“)
- Devices nach **Individualadresse**
- GroupRanges ohne `GR-n` / `Id`
- unlinked COs verwerfen

Stattdessen **additive** Keys (`ets_id`, Identifier behalten). Details: [reference.md](reference.md).

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
