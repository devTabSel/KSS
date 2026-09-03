"""ETS version lookup ``E(entity, t)``.

``t is None`` → current = ``max(last_modified)``.
HTTP at ``t``: ``max(last_modified) <= t``. Request header ``resolution``
(default ``assumed``): if ``E`` is missing, take ``min(last_modified) > t``.
``resolution: exact`` omits that fallback.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

T = TypeVar("T")
E = TypeVar("E")
K = TypeVar("K", bound=Hashable)


@dataclass
class Lookup:
    at: datetime | None = None
    assumed: bool = False
    allow_assumed: bool = True


_lookup: ContextVar[Lookup | None] = ContextVar("kss_lookup", default=None)


@dataclass(frozen=True)
class Resolved[T]:
    row: T
    assumed: bool


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def isoformat_utc(value: datetime) -> str:
    return aware_utc(value).isoformat().replace("+00:00", "Z")


def _current_lookup() -> Lookup:
    lookup = _lookup.get()
    if lookup is None:
        lookup = Lookup()
        _lookup.set(lookup)
    return lookup


def activate_lookup(lookup: Lookup) -> None:
    _lookup.set(lookup)


def begin_lookup(at: datetime | None, *, allow_assumed: bool = True) -> Lookup:
    lookup = Lookup(at=at, assumed=False, allow_assumed=allow_assumed)
    _lookup.set(lookup)
    return lookup


def lookup_at() -> datetime | None:
    return _current_lookup().at


def lookup_allows_assumed() -> bool:
    return _current_lookup().allow_assumed


def lookup_was_assumed() -> bool:
    return _current_lookup().assumed


def note_assumed() -> None:
    _current_lookup().assumed = True


def take_version(versions: list[T], at: datetime | None) -> T | None:
    """HTTP/snapshot lookup honoring the request ``resolution`` policy."""
    return _take(resolve_version(versions, at))


def version_at(versions: list[T], at: datetime | None) -> T | None:
    """Exact ``E(entity, t)``. No future-version assumption."""
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


def resolve_version(versions: list[T], at: datetime | None) -> Resolved[T] | None:
    """HTTP lookup: exact ``E(entity, t)``, else first version after ``t``."""
    if not versions:
        return None
    if at is None:
        return Resolved(
            max(versions, key=lambda item: item.last_modified), assumed=False
        )
    threshold = aware_utc(at)
    earlier = [
        item for item in versions if aware_utc(item.last_modified) <= threshold
    ]
    if earlier:
        return Resolved(max(earlier, key=lambda item: item.last_modified), assumed=False)
    later = [item for item in versions if aware_utc(item.last_modified) > threshold]
    if not later:
        return None
    return Resolved(min(later, key=lambda item: item.last_modified), assumed=True)


def _take(resolved: Resolved[T] | None) -> T | None:
    if resolved is None:
        return None
    if resolved.assumed and not lookup_allows_assumed():
        return None
    if resolved.assumed:
        note_assumed()
    return resolved.row


def pairs_at(entities: Iterable[E]) -> list[tuple[E, object]]:
    at = lookup_at()
    rows: list[tuple[E, object]] = []
    for entity in entities:
        versions = entity.versions
        if not versions:
            continue
        chosen = _take(resolve_version(list(versions), at))
        if chosen is None:
            continue
        rows.append((entity, chosen))
    return rows


def item_at(entity: E | None) -> tuple[E, object] | None:
    if entity is None or not entity.versions:
        return None
    chosen = _take(resolve_version(list(entity.versions), lookup_at()))
    if chosen is None:
        return None
    return entity, chosen


def linked_keys(
    edges: list[T],
    *,
    key: Callable[[T], K],
) -> list[K]:
    grouped: dict[K, list[T]] = {}
    for edge in edges:
        grouped.setdefault(key(edge), []).append(edge)
    keys: list[K] = []
    at = lookup_at()
    for item_key, versions in grouped.items():
        chosen = _take(resolve_version(versions, at))
        if chosen is None:
            continue
        if chosen.linked:
            keys.append(item_key)
    return keys


def linked_ids(
    edges: list[T],
    *,
    key: Callable[[T], UUID],
) -> list[UUID]:
    return sorted(linked_keys(edges, key=key))
