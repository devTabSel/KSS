"""ETS version lookup ``E(entity, t)``.

``t is None`` → current = ``max(last_modified)``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

T = TypeVar("T")


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def isoformat_utc(value: datetime) -> str:
    return aware_utc(value).isoformat().replace("+00:00", "Z")


def version_at(versions: list[T], at: datetime | None) -> T | None:
    if not versions:
        return None
    if at is None:
        return max(versions, key=lambda item: item.last_modified)
    threshold = aware_utc(at)
    candidates = [
        item for item in versions if aware_utc(item.last_modified) <= threshold
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.last_modified)
