# KSS — fachliche Dokumentation

Für **Nutzer von KSS**: Betrieb, Client-Anbindung, später Home Assistant. Keine SQLAlchemy-Internals.

KSS speichert die Semantik einer KNX-Installation **einmal** aus einem ETS-Export und gibt sie über HTTP wieder aus. Clients sollen `.knxproj` nicht selbst parsen.

## Verträge

| URL | Für wen | Inhalt |
| --- | --- | --- |
| `/api/v1` | KNX IoT 3rd Party API | nur spezifizierte 3API-Felder |
| `/api/kss` | KSS-Clients | dieselben Ressourcen plus KSS-Attribute (`kss:`) und Extra-Verben |

Beide Bäume liefern JSON:API (`application/vnd.api+json`).

## Was heute geht

- ETS-Projekt als `.knxproj` (XML-Schema 23) per `PATCH /api/kss/installations` einspielen
- Installationen listen und einzeln lesen (`GET …/installations`, `GET …/installations/{id}`)
- Unter `/api/kss` zusätzliche Attribute, u. a. `kss:lastImport` (Zeitpunkt des letzten Imports)

Details: [api.md](api.md), [begriffe.md](begriffe.md), [stand.md](stand.md).

Technische Gegenstücke: [`docs/technical/`](../technical/README.md). Archiv: [`docs/evolving/`](../evolving/README.md) — nicht verbindlich.
