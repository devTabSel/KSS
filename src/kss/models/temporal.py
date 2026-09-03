"""KSS-Temporalität für historisierte semantische Entitäten.

Kanonisch für alle Versionstabellen (Installation, Location, Topology, Device,
GroupAddress, Trade, temporale Kanten).

Erkenntnisse A–E (Kurz)
    A: Neue Version nur bei semantischem Diff; ``last_modified`` kommt aus ETS,
       nicht aus der Import-Uhr.
    B: Bus-wirksam frühestens ab ``last_downloaded``, wenn jeweilige ``*Loaded``-
       Flags true sind (materialisiert in ``bus_*_bindings``).
    C: Telegramme nutzen BUS-Indizes, dann ETS-Lookup ``E(entity, t)``.
    D: ETS-Semantik in ``*_versions``; BUS-Bindings getrennt materialisiert.
    E: PA- und GA-Bindings können zu unterschiedlichen ``last_downloaded``
       springen.

Versionsschlüssel
    ``last_modified`` (NOT NULL, PK-Teil) ist der einzige ETS-Versionsschlüssel
    und gleichzeitig 3API ``lastModified``, wo zutreffend. Wert beim Import:
    Objekt-``LastModified``, sonst ``ProjectInformation/@LastModified``.

Import-Uhr
    ``installations.last_import`` (UTC) wird bei jedem PATCH-Ingest gesetzt.
    Ersetzt ``_observable_since`` auf Versionen.

Anlegen / Änderung
    Neue Version nur bei Änderung semantisch relevanter Felder.
    Gleiches ``(entity_id, last_modified)``: keine zweite Zeile.
    Historische Zeilen werden nicht aktualisiert.

Lookup ETS
    ``E(entity, t) =`` Zeile mit ``max(last_modified) <= t``.

Lookup BUS
    PA: ``max(last_downloaded) <= t`` in ``bus_pa_bindings``.
    GA: alle Zeilen mit ``group_address = g`` und ``max(last_downloaded) <= t``
    pro ``(installation_id, device_id)``.
"""

from datetime import datetime

from sqlalchemy import DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column


class TemporalVersionMixin:
    last_modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "ETS-Versionsschlüssel (UTC) und 3API lastModified wo zutreffend. "
            "Objekt-LastModified, sonst Projekt-LastModified. "
            "Ende = nächstes last_modified derselben Identität."
        ),
    )


def version_primary_key(*entity_id_columns: str) -> PrimaryKeyConstraint:
    return PrimaryKeyConstraint(*entity_id_columns, "last_modified")
