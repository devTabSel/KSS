# Begriffe

**Installation** — ein ETS-Projekt in KSS. Identität ist die 3API-UUID. Wiedererkennung beim Import über die Projekt-GUID.

**Aktueller Stand** — die Version mit dem größten `lastModified` (ETS-Änderungszeit). Das ist nicht die Uhr, zu der KSS die Datei eingelesen hat.

**Stand zu t** — die Version mit dem größten `lastModified`, das nicht nach `t` liegt. Ohne solche Zeile gibt es den Stand nicht (HTTP **404**). Datei-Export und JSON-GET `?at=` (nur `/api/kss`) nutzen denselben Zeitpunkt.

**lastImport** (`kss:lastImport`) — wann KSS den letzten PATCH-Ingest für diese Installation ausgeführt hat. Unabhängig von `lastModified`. Nicht Teil der Versionsidentität.

**3API vs. KSS** — `/api/v1` spricht nur die offizielle KNX IoT 3rd Party API. `/api/kss` ergänzt herstellereigene Attribute mit Präfix `kss:` und nimmt Datei-Import und Datei-Export entgegen.

**ETS vs. BUS** — ETS-Attribute (Namen, Adressen im Projekt, Fertigstellungsstatus, …) versioniert KSS mit `lastModified`. Was auf dem Bus wirksam ist (Individualadresse, Gruppenbindung nach Download), ist ein eigener Bestand. Telegramm-Auswertung über die Zeit ist geplant; HTTP dafür gibt es noch nicht.

**Location / Function / Device / Datapoint** — weitere 3API-Entitäten. Schema, knxproj-Ingest und GET (Collection/Item) sind angeschlossen. Trade, Topologie und Geräte-Kanäle kommen aus dem knxproj (Trade auch aus KSS-TTL); GET dafür nur unter `/api/kss`.

**Semantic Export (ETS-TTL)** — ETS exportiert KIM als Turtle (`.ttl`). Dieselbe Projekt-GUID wie die `.knxproj` ergibt eine Installation. ETS-Dateien enthalten typischerweise keine Gewerke `prj:T-*`; der Gewerkename am Gerät (`kss:assignedTrade`) kommt aus `mac:assignedTrade`. Topologie, Kanäle und BUS entstehen daraus nicht.

**KSS-TTL** — von KSS geschriebenes Turtle (canonical). Enthält die knxproj-Gewerke als `prj:T-*` und roundtrippt (Export → Import → Export identisch).
