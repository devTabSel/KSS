# KSS — fachliche Dokumentation

Für **Nutzer von KSS**: Betrieb, Client-Anbindung, später Home Assistant. Keine SQLAlchemy-Internals.

KSS speichert die Semantik einer KNX-Installation **einmal** und gibt sie über HTTP wieder aus. Clients sollen ETS-Exporte nicht selbst parsen.

Einspielbar: ETS-Projekt als `.knxproj` und ETS Semantic Export als `.ttl` (KIM-RDF). Beide bezeichnen dieselbe Installation, wenn die Projekt-GUID gleich ist.

## Verträge

| URL | Für wen | Inhalt |
| --- | --- | --- |
| `/api/v1` | KNX IoT 3rd Party API | nur spezifizierte 3API-Felder |
| `/api/kss` | KSS-Clients | dieselben Ressourcen plus KSS-Attribute (`kss:`) und Extra-Verben |

Beide Bäume liefern JSON:API (`application/vnd.api+json`). Datei-Export nur unter `/api/kss`.

## Was heute geht

- `.knxproj` (XML-Schema 23) oder `.ttl` (Semantic Export / KSS-Turtle) per `PATCH /api/kss/installations` einspielen
- Installationsstand zu einem Zeitpunkt `t` als JSON oder Datei (`.ttl` / `.knxproj`) unter `/api/kss/{t}/…` ausgeben
- Installationen, Locations, Functions, Devices und Datapoints listen und einzeln lesen
- Unter `/api/kss` zusätzliche Attribute, u. a. `kss:lastImport` und am Device `kss:assignedTrade`, `kss:hardwareProgramRef`
- Bestellnummer und Herstellername am Device aus dem globalen Produktkatalog

Details: [api.md](api.md), [begriffe.md](begriffe.md), [stand.md](stand.md).

Technische Gegenstücke: [`docs/technical/`](../technical/README.md). Archiv: [`docs/evolving/`](../evolving/README.md) — nicht verbindlich.
