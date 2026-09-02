# HTTP für Nutzer

Medien-Typ: `application/vnd.api+json`. Fehlerhülle analog 3API (`errors[]` mit `title`, `status`, `detail`).

## Lesen

| Methode | Pfad | Hinweis |
| --- | --- | --- |
| GET | `/api/v1/installations` | Collection, nur 3API-Attribute |
| GET | `/api/v1/installations/{id}` | Item |
| GET | `/api/kss/installations` | Collection plus `kss:` |
| GET | `/api/kss/installations/{id}` | Item plus `kss:` |

Pagination: Query `page[number]` (Default 0), `page[size]` (Default 65536). Collection-`meta.collection` ist gesetzt.

Item: `data.type` = `installation`, `data.id` = UUID, `attributes.title` immer. Leere `relationships` entfallen.

3API-Attribute (wenn vorhanden): `title`, `comment`, `contractNumber`, `lastModified`, `projectInstallationNumber`, `state` (Fertigstellungsstatus). Optional `meta.typedescription`.

KSS-Attribute nur unter `/api/kss`: `kss:etsId`, `kss:projectGuid`, `kss:installationIndex`, `kss:groupAddressStyle`, `kss:masterDataVersion`, `kss:projectType` (XML-Token, z. B. `Family House`), `kss:lastImport`.

## Import

Nur unter `/api/kss`, nicht unter `/api/v1`.

`PATCH /api/kss/installations` (Collection, multipart):

| Feld | Pflicht | Bedeutung |
| --- | --- | --- |
| `file` | ja | Dateiinhalt |
| `filename` | nein | Dateiname; sonst `file.filename` |
| `created` | nein | wird nicht persistiert |
| `password` | nein | Passwort der `.knxproj` |

Erfolg: **201** neue Installation, **204** bestehende aktualisiert. Kein Response-Body.

| Suffix | Ergebnis |
| --- | --- |
| `.knxproj` | Import, Schema 23 |
| `.ttl` | **501** Not Implemented |
| sonst | **422** |

Identität beim Wieder-Import: dieselbe Projekt-GUID → dieselbe Installation, neue Version nur wenn sich semantische Felder geändert haben.

## Auth

Keine. OAuth kommt später; es gibt keine Fake-401.
