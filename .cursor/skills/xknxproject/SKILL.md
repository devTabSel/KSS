---
name: xknxproject
description: >-
  Additive xknxproject fork (devTabSel/xknxproject): origin
  github.com/devTabSel/xknxproject, upstream github.com/XKNX/xknxproject.
  One parse(combine=True default); KSS uses parse(combine=False). Extra keys
  only on combine=False. GitHub fork/PR/rebase. Use when changing the
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
- Extra Keys (inkl. `info`, `ets_id`, GOT, `trades`) nur bei `parse(combine=False)`. Default `parse()` / `parse(combine=True)` ist das HA-Dict ohne diese Keys.
- Nicht additiv (verboten ohne Nutzerentscheid): Encoding/Typ eines Upstream-Werts ändern (z. B. Base64→Hex), Omit-Defaults (`""`/`false` → `null`), Sentinel-Mapping, Dict-Keys umschlüsseln.

Typen: `xknxproject/models/knxproject.py`. Einstieg: `xknxproject/xknxproj.py`. XML: `xknxproject/xml/parser.py`, Loader unter `xknxproject/loader/`.

## `info` (Stand Installation)

Bereits upstream-ähnlich: `project_id`, `name`, `last_modified`, `group_address_style`, `guid`, `created_by`, `schema_version`, `tool_version`, `xknxproject_version`, `language_code`.

KSS-additiv, nur `parse(combine=False)`: `installation_index`, `ets_id`, `completion_status` (XML-Omit → `Undefined`), `comment`, `master_data_version`, `project_number`, `contract_number`, `project_type` (XML-Token, z. B. `Family House`), `project_start` (`ProjectInformation/@ProjectStart`, ISO-String wie in XML), `bcu_key` (`Installation/@BCUKey` in `0.xml`), `ip_routing_backbone_key` (`Installation/@IPRoutingBackboneKey` in `0.xml`). Leer/Omit → `null`. Keine IP-Latenzen, BusAccess, Hashes, ToDos, LastUsedPuid, ArchivedVersion. Default-`parse()` hat diese Keys nicht.

Sprachlabels (`Familienhaus`) nicht erfinden. Schema **≥ 23** lehnt KSS ab, der Parser darf ältere Projekte weiter lesen.

## `locations` / Space (additiv, Dict weiter nach Name)

`locations` bleibt nach **Name** geschlüsselt (`_recursive_convert_spaces`). Additive Keys auf jedem Space, nur `parse(combine=False)`:

| key | Quelle | Leer/Omit |
| --- | --- | --- |
| `ets_id` | Suffix von `@Id` nach dem letzten `_` (`P-040E-0_BP-1` → `BP-1`) | immer, Pflicht |
| `comment` | `@Comment` | `null` |
| `completion_status` | `@CompletionStatus` | `null` (kein `Undefined` erfinden; Space-Omit ist üblich) |
| `last_modified` | `@LastModified` | `null` (KSS fällt auf Project-LastModified zurück) |
| `default_line` | Suffix von `@DefaultLine` (`P-040E-0_L-5` → `L-5`) | `null` |

Bestehend bleibt: `identifier` (volle Id), `usage_id` (roh `@Usage`, auch `tag:`), `usage_text`, `type`, `name`, `number`, `description`, nested `spaces`, `functions`, `devices` (weiter IA).

## `topology` / Area / Line / Segment (additiv, Dict weiter nach Address)

`topology` bleibt nach **Area-Address** geschlüsselt, `lines` nach **Line-Address**. Additive Keys, nur `parse(combine=False)`:

| Objekt | key | Quelle | Leer/Omit |
| --- | --- | --- | --- |
| Area, Line, Segment | `ets_id` | Suffix von `@Id` (`A-n` / `L-n` / `S-n`) | immer, Pflicht |
| Area, Line, Segment | `identifier` | volle `@Id` | `""` wenn omit |
| Area, Line | `address` | `@Address` (int, auch Dict-Key) | immer |
| Area, Line, Segment | `completion_status` | `@CompletionStatus` | `null` |
| Area, Line, Segment | `last_modified` | `@LastModified` | `null` |
| Line, Segment | `medium_type_ref` | `MediumTypeRefId` (`MT-*`) | `null` |
| Line | `segments` | alle `Segment`-Kinder (nicht nur das erste) | `[]` |

`medium_type` bleibt die HA-Bezeichnung (`Twisted Pair (TP)` …). ETS-4/5 ohne Segment: `segments=[]`, Medium weiter vom Line-Attribut.

## `devices` / Device (additiv, Dict weiter nach Individualadresse)

`devices` bleibt nach **Individualadresse** geschlüsselt. Additive Keys, nur `parse(combine=False)`:

| key | Quelle | Leer/Omit |
| --- | --- | --- |
| `ets_id` | Suffix von `@Id` (`P-040E-0_DI-1` → `DI-1`) | immer, Pflicht |
| `identifier` | volle `@Id` | `""` wenn omit |
| `comment` | `@Comment` | `null` |
| `completion_status` | `@CompletionStatus` | `null` |
| `last_modified` | `@LastModified` | `null` |
| `product_ref` | `@ProductRefId` | `null` |
| `hardware_program_ref` | `@Hardware2ProgramRefId` | `null` |
| `installation_hints` | `@InstallationHints` | `null` |
| `segment_ets_id` | Parent-`Segment` Suffix `S-n` | `null` (ETS-4/5 ohne Segment) |

Geräte ohne `@Address` bleiben aus dem Dict (HA). `application` bleibt die gemergte ApplicationProgram-Ref.

Upstream-Felder am Device (nicht umkodieren, gleiche Werte wie XKNX):

- `serial_number` roh `@SerialNumber` Base64, Typ `str`, Omit → `""`. Hex-Konvertierung ist nicht additiv.
- `last_download` roh `@LastDownload`, Typ `str | None`; Attribut fehlt → `null`; Sentinel `0001-01-01…` bleibt der String. Sentinel-Drop ist **KSS-Importer**, nicht der Fork.
- `*Loaded` (`IndividualAddressLoaded`, `CommunicationPartLoaded`, `ApplicationProgramLoaded`, `ParametersLoaded`, `MediumConfigLoaded`): `elem.get("X") == "true"`, Typ `bool`, Omit → `false`. Omit→null ist nicht der Fork; KSS-Importer mapped fehlend/None → False.

Additive Device-Keys, nur `parse(combine=False)` (`{}` wenn leer). HA-`channels` (nur Nodes mit GroupObjectInstances) und Top-Level-`communication_objects` (nur COs mit gültigen Links) unverändert.

`group_object_tree.channels` keyed by Channel-`ets_id`: mit ChannelInstance `split("_", 1)[1]` von `@Id` (`P-040E-0_DI-11_CI-2` → `DI-11_CI-2`, nicht `rsplit`/`CI-2`); ohne Instance = GOT Node `@RefId`. Join Instance↔Node über `@RefId`. Leere Kanäle und nested Channel (`parent_channel_ets_id`) gehören dazu.

`group_object_tree.folders` keyed by `PB-*`; XOR `parent_folder_ets_id` / `parent_channel_ets_id`.

`comm_objects` keyed by `O-…_R-…`, **alle** COs inkl. ohne Links (`group_address_ets_ids` darf `[]` sein). `datapoint_subtype_ets_id` aus `@DatapointType`. `channel_ets_id` über ChannelId→catalog_ref. `folder_ets_id` innerster Folder, der das CO listet.

## `functions` / Function (additiv)

`parse_functions` setzt `identifier` weiter auf Suffix `F-n`. Additive Keys, nur `parse(combine=False)`:

| key | Quelle |
| --- | --- |
| `ets_id` | gleich `identifier` (`F-n`), auch wenn redundant |
| `description` | `@Description`, leer → `null` |
| `comment` | `@Comment`, leer → `null` |
| `completion_status` | `@CompletionStatus`, omit → `null` |
| `last_modified` | `@LastModified`, omit → `null` |

Bestehend: `function_type`, `space_id` (volle Space-Id), `group_addresses`, `usage_text`.
`group_addresses` (Display-Adresse als Key) additiv: `identifier`, `ets_id` (`GF-n` aus Ref-`@Id`), `ga_ets_id` (`GA-n` = `ref_id`).

## `group_addresses` / GroupAddress (additiv, Dict weiter nach Display-Adresse)

`group_addresses` bleibt nach **Display-Adresse** geschlüsselt (`15/0/0`). Additive Keys, nur `parse(combine=False)`:

| key | Quelle | Leer/Omit |
| --- | --- | --- |
| `ets_id` | Suffix von `@Id` (`P-040E-0_GA-17296` → `GA-17296`); gleich `identifier` | immer |
| `datapoint_type_ref` | `@DatapointType` Token `DPST-*` / `DPT-*` | `null` |
| `completion_status` | `@CompletionStatus` | `null` |
| `last_modified` | `@LastModified` | `null` |
| `unfiltered` / `central` / `global_` | `@Unfiltered` / `@Central` / `@Global` (`true`/`false`) | `null` |
| `purpose` / `security` | `@Purpose` / `@Security` | `null` |
| `key` | `@Key` roh (Base64); bestehendes `data_secure` bleibt bool | `null` |

Bestehend bleibt: `address`, `raw_address`, `dpt` (HA-DPTType), `data_secure`, `communication_object_ids`, Name/Beschreibung/Kommentar.

## `group_ranges` / GroupRange (additiv, Dict weiter nach `str_address()`)

`group_ranges` bleibt nach **Range-Anzeige** geschlüsselt (`15`, `15/0`). Additive Keys, nur `parse(combine=False)`:

| key | Quelle | Leer/Omit |
| --- | --- | --- |
| `ets_id` | Suffix von `@Id` (`GR-n`) | `""` wenn omit |
| `identifier` | volle `@Id` | `""` wenn omit |
| `description` | `@Description` | `null` |
| `completion_status` | `@CompletionStatus` | `null` |
| `last_modified` | `@LastModified` | `null` |
| `unfiltered` / `security` | `@Unfiltered` / `@Security` | `null` |

Nested `group_ranges` und `group_addresses` (Liste Display-Adressen) unverändert.

Leere XML-Strings → `None` via `_optional_xml_str`. Default-`parse()` muss zu HA-Stubs passen (keine Extra-Keys). `assert_stub` erlaubt extra Keys, falls ein Test `combine=False` gegen dieselben Stubs hält.

## `trades` / Trade (additiv, Dict nach `T-n`)

`trades` ist ein Top-Level-Key nur bei `parse(combine=False)` (leer `{}` wenn XML keine Trades hat). Default-`parse()` hat den Key nicht. **Key = `ets_id` (`T-n`)**, nicht `@Name` (Namen dürfen kollidieren). Nested `trades` ebenso. Additive Keys:

| key | Quelle | Leer/Omit |
| --- | --- | --- |
| `ets_id` | Suffix von `@Id` (`P-040E-0_T-46` → `T-46`) | immer wenn Id da |
| `identifier` | volle `@Id` | `""` wenn omit |
| `name` | `@Name` | `""` |
| `number` | `@Number` | `null` |
| `description` | `@Description` | `null` |
| `comment` | `@Comment` (RTF unescaped) | `null` |
| `completion_status` | `@CompletionStatus` | `null` |
| `last_modified` | `@LastModified` | `null` |
| `devices` | `DeviceInstanceRef/@RefId` Suffix `DI-n` | `[]` |
| `trades` | nested `Trade` | `{}` |

Kein `puid`. Kein Umschlüsseln auf Device-IA.

## `master_data` (`combine=False` only)

`parse(combine=False)` hängt den Top-Level-Key **`master_data`** an: knx_master-Katalog (DPT/DPST, datafields, FunctionTypes, Roles, SpaceUsages `SU-*`, MediumTypes, FunctionPoints, Manufacturers) plus **`translations`** für alle Sprachen außer en-US. Inline `@Text`/`@Name` auf den Entities ist der en-US-Default; `language=` overlayt diesen Katalog **nicht**. Default `parse()` / `parse(combine=True)` hat **kein** `master_data` (HA-Pfad bleibt billig, keine Languages-Walk).

## Nicht umschlüsseln

Bekannte Upstream-Lücken — KSS darf sie nicht „wegfixen“ durch andere Keys:

- Locations nach **Name** (`_recursive_convert_spaces`; test_A: doppelte „Raum 1“)
- Devices nach **Individualadresse**
- GroupAddresses nach **Display-Adresse**; GroupRanges nach **`str_address()`**
- unlinked COs: HA-`communication_objects` verwirft sie weiter; Device-`comm_objects` behält sie

Stattdessen **additive** Keys (`ets_id`, Identifier behalten). Details: [reference.md](reference.md). Keine fertigen KIM-IRIs / `meta.@type` im Parser — Tokens (`FT-*`, `DPST-*`, Space Type, Usage); Synthese in KSS (Tag-Store). [3API-Plan](../../plans/kss-and-knx-3rd-party-api.md).

## GitHub / Fork

1. Vor Parser-Arbeit: `git fetch upstream` und Stand relativ zu `upstream/main` kennen.
2. Additive Commits auf einem Fork-Branch; Default `combine` und Stub-JSON für bestehende Tests nicht brechen.
3. Tests im Fork (`test/`, Stubs unter `test/resources/stubs/`). KSS-XSD-Korpus: alle `research/*.knxproj` (WA53H10 produktiv; `test_A*` Reverse Engineering, z. B. doppelte „Raum 1“). TTL: alle `research/*.ttl`, Skill `knx-semantik`, nicht in den Fork.
4. Upstream-PR nur für Änderungen, die XKNX nützen (keine KSS-only-Hacks, keine Persistenz).
5. `gh pr create` / `gh pr view` / Checks. Kein force-push auf `main`. Kein `git config` ändern.
6. Andere [XKNX](https://github.com/XKNX/)-Repos (`xknx`, `knx-integration`, `knx-frontend`) nicht anfassen, bis der Nutzer das verlangt.

### Upstream-Merge: nur additiv, sonst stoppen

Fork darf Upstream **nur additiv** ändern: neue Keys, gleiche Werte/Typen/Defaults für alles, was XKNX schon liefert.

Bei einem Merge-Konflikt an einem Feld, das Upstream bereits hat (oder gerade einführt): **nicht selbst mergen**. Konflikt stehen lassen oder abbrechen, dann dem Nutzer schildern:

- Datei und Key
- ours vs theirs (Wert, Typ, Omit-Default, Encoding)
- warum das nicht additiv wäre (HA sähe einen anderen String/Typ)
- was KSS braucht, falls überhaupt etwas

Erst nach ausdrücklicher Entscheidung mergen. Beispiel verboten: `serial_number` Base64→Hex, obwohl Upstream denselben Key als Base64-`str` mit Omit `""` hat.

## Nicht tun

- KSS-REST, Alembic (TTL/Join/BUS: Representer mit Skill `knx-semantik`, nicht hier)
- Locations/Devices umschlüsseln
- `combine`-Default ändern
- Eigenparser in KSS
- Nicht-additive Konflikte mit Upstream selbst mergen (Encoding, Typ, Omit-Default)
