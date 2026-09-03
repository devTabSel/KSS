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

Device 3API: `orderNumber` und `manufacturer` aus dem Produktkatalog (Join über die Produkt-Referenz). Fehlt die Referenz oder die Katalogzeile, entfallen die Attribute.

Device unter `/api/kss` zusätzlich, wenn gesetzt: `kss:assignedTrade` (Gewerkename aus dem Semantic Export), `kss:operatesForTrade` (nur wenn nicht leer), `kss:hardwareProgramRef`. `assignedTrade` gibt es nicht unter `/api/v1` und nicht als 3API-Feld.

JSON-GET und Datei-Export zum Zeitpunkt `t`: `GET /api/kss/{t}/installations/{id}` (ISO-8601, `:` in der URL kodiert). Ohne `{t}` = aktueller Stand. `/api/v1` immer aktuell. Ungültiges `{t}` → **422**. Request-Header `resolution` (nur `/api/kss/{t}/…`): Default `assumed`; `exact` = Schnitt ohne Annahme; anderer Wert → **422**. Response-Header `resolution`: `exact` oder `assumed` (letzteres, sobald ein Paket oder eine Kante angenommen wurde). Query `?at=` wird ignoriert.

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
| `.ttl` | Semantic Export oder KSS-Turtle (KIM-RDF); Passwort und `Accept-Language` werden ignoriert |
| sonst | **422** (`supported now: .knxproj, .ttl`) |

Unlesbare oder unsinnige Datei: **422**. Identität beim Wieder-Import: dieselbe Projekt-GUID → dieselbe Installation, neue Version nur wenn sich semantische Felder geändert haben.

`.ttl` ist Turtle derselben Anlage wie `.knxproj`. ETS Semantic Export enthält typischerweise keine Gewerke `T-n`. KSS-exportiertes Turtle enthält `prj:T-*` und roundtrippt. Nur-ETS-TTL liefert keine Topologie. Erst knxproj, dann TTL unter derselben GUID füllt Zusatzfelder nach (z. B. Gewerkename am Gerät).

## Export

Nur unter `/api/kss`, nicht unter `/api/v1`. Dasselbe Item-GET: `GET /api/kss/installations/{id}`.

KSS rekonstruiert den Stand aus der versionierten Datenbank. Originaldateien werden nicht gespeichert. Kein Passwort; knxproj-ZIP unverschlüsselt.

| Query | Bedeutung |
| --- | --- |
| `format` | `.ttl` / `.knxproj` (auch `turtle` / `zip`); überschreibt Accept |
| `at` | ISO-8601; weglassen = aktueller Stand |
| `less_info` | nur knxproj, Default **true** (schlanker Export) |

Accept (erster Typ): `text/turtle` oder `text/ttl` → Turtle; `application/vnd.knx.knxproj+zip`, `application/zip` oder `application/x-knxproj` → knxproj. Ohne Datei-Negotiation bleibt JSON:API.

Datei-Antwort: Rohkörper, `Content-Disposition: attachment; filename="{title}.ttl|.knxproj"`.

`/api/v1` mit Datei-Accept oder `format` → **406** (`file export is only available under /api/kss`). Ungültiges `format` oder `at` → **422**. Keine Version `<= at` → **404**.

## Auth

Keine. OAuth kommt später; es gibt keine Fake-401.
