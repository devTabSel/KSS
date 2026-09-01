"""KSS-Temporalität für historisierte semantische Entitäten.

Kategorie-3-Spalten (führender Unterstrich, nicht Bestandteil der 3API):

- ``_since``: Gültigkeitsbeginn dieser Version (UTC, DST-unabhängig).
  Quelle je Objektklasse: siehe Skill ``knx-import`` (Device: echtes
  LastDownload, sonst LastModified; übrige: LastModified bzw. Projekt).
  Teil des Primärschlüssels.
- ``_observable_since``: Zeitpunkt, zu dem KSS diese Version erstmals
  beobachtet hat (UTC). Quelle: Import. Nicht Teil des Primärschlüssels.

Eine Version gilt von ``_since`` bis zum nächsten ``_since`` derselben
Identität (halb-offen). Aktuell = ``max(_since)``. Historische Zeilen werden
nicht aktualisiert. Identisches ``_since`` erzeugt keine zweite Version.
"""

from datetime import datetime

from sqlalchemy import DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column


class TemporalSinceMixin:
    _since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "KSS Kategorie 3. Gültigkeitsbeginn dieser Version (UTC). "
            "ETS-Projekt- bzw. Bus-wirksame Änderung. "
            "Ende = nächstes _since derselben Identität."
        ),
    )
    _observable_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "KSS Kategorie 3. Zeitpunkt, zu dem KSS diese Version bekannt wurde "
            "(UTC, Import)."
        ),
    )


def since_primary_key(*entity_id_columns: str) -> PrimaryKeyConstraint:
    return PrimaryKeyConstraint(*entity_id_columns, "_since")
