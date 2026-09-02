# Begriffe

**Installation** — ein ETS-Projekt in KSS. Identität ist die 3API-UUID. Wiedererkennung beim Import über die Projekt-GUID.

**Aktueller Stand** — die Version mit dem größten `lastModified` (ETS-Änderungszeit). Das ist nicht die Uhr, zu der KSS die Datei eingelesen hat.

**lastImport** (`kss:lastImport`) — wann KSS den letzten PATCH-Ingest für diese Installation ausgeführt hat. Unabhängig von `lastModified`.

**3API vs. KSS** — `/api/v1` spricht nur die offizielle KNX IoT 3rd Party API. `/api/kss` ergänzt herstellereigene Attribute mit Präfix `kss:` und nimmt den Datei-Import entgegen.

**ETS vs. BUS** — ETS-Attribute (Namen, Adressen im Projekt, Fertigstellungsstatus, …) versioniert KSS mit `lastModified`. Was auf dem Bus wirksam ist (Individualadresse, Gruppenbindung nach Download), ist ein eigener Bestand. Telegramm-Auswertung über die Zeit ist geplant; HTTP dafür gibt es noch nicht.

**Location / Device / Datapoint / Trade** — weitere 3API- bzw. knxproj-Entitäten. Das Schema kennt sie; HTTP-Ingest und GET dafür sind noch nicht angeschlossen.

**Semantic Export (TTL)** — geplanter zweiter Ingest derselben Installation. Noch nicht implementiert (HTTP 501).
