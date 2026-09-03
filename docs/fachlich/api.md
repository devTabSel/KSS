# HTTP für Nutzer

Medien-Typ: `application/vnd.api+json`. Fehlerhülle analog 3API (`errors[]` mit `title`, `status`, `detail`).

Beziehungen im Ist sind Resource Identifier (`type` + `id`), keine eingebetteten Ressourcen.

## Lesen (beide Prefixes)

Collection und Item, Pagination: Query `page[number]` (Default 0), `page[size]` (Default 65536). Collection-`meta.collection` ist gesetzt. `data.id` ist die UUID.

| Methode | Pfad |
| --- | --- |
| GET | `…/installations`, `…/installations/{id}` |
| GET | `…/locations`, `…/locations/{id}` |
| GET | `…/functions`, `…/functions/{id}` |
| GET | `…/devices`, `…/devices/{id}` |
| GET | `…/datapoints`, `…/datapoints/{id}` |

`/api/v1` nur 3API-Attribute. `/api/kss` dieselben Ressourcen plus `kss:` (u. a. `kss:etsId`, `kss:lastImport` an der Installation).

Installation: `data.type` = `installation`, `attributes.title` immer. Leere `relationships` entfallen.

3API-Attribute der Installation (wenn vorhanden): `title`, `comment`, `contractNumber`, `lastModified`, `projectInstallationNumber`, `state` (Fertigstellungsstatus). Optional `meta.typedescription`.

KSS-Attribute nur unter `/api/kss`: `kss:etsId`, `kss:projectGuid`, `kss:installationIndex`, `kss:groupAddressStyle`, `kss:masterDataVersion`, `kss:projectType` (XML-Token, z. B. `Family House`), `kss:lastImport`.

Device unter `/api/kss` zusätzlich, wenn gesetzt: `kss:assignedTrade` (Gewerkename aus dem Semantic Export), `kss:operatesForTrade` (nur wenn nicht leer). Beides gibt es nicht unter `/api/v1` und nicht als 3API-Feld `assignedTrade`.

## Lesen nur `/api/kss`

Kein 3API-Pendant: Areas, Lines, Segments, Trades, GroupRanges, Channels, Folders, CommObjects.

## Import

Nur unter `/api/kss`, nicht unter `/api/v1`.

`PATCH /api/kss/installations` (Collection, multipart):

| Feld | Pflicht | Bedeutung |
| --- | --- | --- |
| `file` | ja | Dateiinhalt |
| `filename` | nein | Dateiname; sonst `file.filename` |
| `created` | nein | wird nicht persistiert |
| `password` | nein | nur `.knxproj` |

Erfolg: **201** neue Installation, **204** bestehende aktualisiert. Kein Response-Body.

| Suffix | Ergebnis |
| --- | --- |
| `.knxproj` | Import, Schema 23; Passwort und `Accept-Language` gelten |
| `.ttl` | Semantic Export (KIM-RDF); Passwort und `Accept-Language` werden ignoriert |
| sonst | **422** (`supported now: .knxproj, .ttl`) |

Unlesbare oder unsinnige Datei: **422**. Identität beim Wieder-Import: dieselbe Projekt-GUID → dieselbe Installation, neue Version nur wenn sich semantische Felder geändert haben.

`.ttl` ist der ETS Semantic Export derselben Anlage wie `.knxproj`. Nur-TTL liefert keine Topologie und keinen Gewerke-Baum. Erst knxproj, dann TTL unter derselben GUID füllt Zusatzfelder nach (z. B. Gewerkename am Gerät).

## Auth

Keine. OAuth kommt später; es gibt keine Fake-401.
