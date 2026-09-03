"""Upsert Trade and TradeDevice from knxproj parse output.

Identity is ``ets_id`` (``T-n``), which is also the trades dict key.
Does not write Device ``assigned_trade`` or KIM tags. Missing entities are not unlinked.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kss.models.constants import COMPLETION_STATUS_VALUES
from kss.models.device import Device
from kss.models.installation import Installation
from kss.models.trade import Trade, TradeDevice, TradeVersion
from kss.services.knxproj import KnxprojImportError, parse_ets_datetime

TRADE_SEMANTIC_FIELDS = (
    "name",
    "number",
    "comment",
    "description",
    "completion_status",
    "parent_trade_id",
)

TRADE_DEVICE_SEMANTIC_FIELDS = ("linked",)


def current_trade_pairs(session: Session) -> list[tuple[Trade, TradeVersion]]:
    trades = session.scalars(
        select(Trade).options(selectinload(Trade.versions)).order_by(Trade.id)
    ).all()
    rows: list[tuple[Trade, TradeVersion]] = []
    for trade in trades:
        if not trade.versions:
            continue
        current = max(trade.versions, key=lambda item: item.last_modified)
        rows.append((trade, current))
    return rows


def get_current_trade(
    session: Session, trade_id: UUID
) -> tuple[Trade, TradeVersion] | None:
    trade = session.get(Trade, trade_id, options=(selectinload(Trade.versions),))
    if trade is None or not trade.versions:
        return None
    current = max(trade.versions, key=lambda item: item.last_modified)
    return trade, current


def upsert_trades_from_project(
    session: Session,
    installation: Installation,
    project: Mapping[str, object],
    fallback_last_modified: datetime,
) -> None:
    fallback = _aware_utc(fallback_last_modified)
    trades_by_ets = _upsert_trades(session, installation, project.get("trades"), fallback)
    _upsert_trade_devices(
        session,
        installation,
        project.get("trades"),
        trades_by_ets,
        fallback,
    )


def _upsert_trades(
    session: Session,
    installation: Installation,
    trades_raw: object,
    fallback: datetime,
) -> dict[str, Trade]:
    by_ets = _trades_by_ets_id(session, installation.id)
    if not isinstance(trades_raw, Mapping):
        return by_ets
    flattened = list(_walk_trades(trades_raw, None))
    new_identities: list[Trade] = []
    for _raw, ets_id, _parent in flattened:
        if ets_id in by_ets:
            continue
        trade = Trade(
            id=uuid4(),
            installation_id=installation.id,
            ets_id=ets_id,
        )
        session.add(trade)
        by_ets[ets_id] = trade
        new_identities.append(trade)
    if new_identities:
        session.flush()
    for raw, ets_id, parent_ets_id in flattened:
        parent_id = None
        if parent_ets_id and parent_ets_id != ets_id:
            parent = by_ets.get(parent_ets_id)
            if parent is not None:
                parent_id = parent.id
        _upsert_trade_version(
            session, by_ets[ets_id], raw, parent_id=parent_id, fallback=fallback
        )
    session.flush()
    return by_ets


def _upsert_trade_devices(
    session: Session,
    installation: Installation,
    trades_raw: object,
    trades_by_ets: dict[str, Trade],
    fallback: datetime,
) -> None:
    if not isinstance(trades_raw, Mapping):
        return
    devices_by_ets = _devices_by_ets_id(session, installation.id)
    existing_edges = _trade_devices_by_pair(session, installation.id)
    for raw, ets_id, _parent in _walk_trades(trades_raw, None):
        trade = trades_by_ets.get(ets_id)
        if trade is None:
            continue
        last_modified = _last_modified(raw.get("last_modified"), fallback)
        refs = raw.get("devices")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            device_ets_id = _ets_id(None, ref)
            if not device_ets_id:
                continue
            device = devices_by_ets.get(device_ets_id)
            if device is None:
                continue
            fields = {"linked": True, "last_modified": last_modified}
            pair = (trade.id, device.id)
            versions = existing_edges.setdefault(pair, [])
            existing_at = next(
                (item for item in versions if item.last_modified == last_modified),
                None,
            )
            if existing_at is not None:
                continue
            if versions:
                current = max(versions, key=lambda item: item.last_modified)
                incoming = tuple(fields[name] for name in TRADE_DEVICE_SEMANTIC_FIELDS)
                existing = tuple(
                    getattr(current, name) for name in TRADE_DEVICE_SEMANTIC_FIELDS
                )
                if incoming == existing:
                    continue
            edge = TradeDevice(
                trade_id=trade.id,
                device_id=device.id,
                **fields,
            )
            session.add(edge)
            versions.append(edge)
    session.flush()


def _upsert_trade_version(
    session: Session,
    trade: Trade,
    raw: Mapping[str, object],
    *,
    parent_id: UUID | None,
    fallback: datetime,
) -> None:
    name = _optional_str(raw.get("name")) or trade.ets_id
    fields = {
        "name": name,
        "number": _optional_str(raw.get("number")),
        "comment": _optional_str(raw.get("comment")),
        "description": _optional_str(raw.get("description")),
        "completion_status": _completion_status(raw.get("completion_status")),
        "parent_trade_id": parent_id,
        "last_modified": _last_modified(raw.get("last_modified"), fallback),
    }
    last_modified = fields["last_modified"]
    existing_at_modified = next(
        (item for item in trade.versions if item.last_modified == last_modified),
        None,
    )
    if existing_at_modified is not None:
        return
    if trade.versions:
        current = max(trade.versions, key=lambda item: item.last_modified)
        incoming = tuple(fields[name] for name in TRADE_SEMANTIC_FIELDS)
        existing = tuple(getattr(current, name) for name in TRADE_SEMANTIC_FIELDS)
        if incoming == existing:
            return
    version = TradeVersion(trade_id=trade.id, **fields)
    session.add(version)
    trade.versions.append(version)


def _walk_trades(
    trades: Mapping[str, object],
    parent_ets_id: str | None,
) -> Iterator[tuple[Mapping[str, object], str, str | None]]:
    for key, raw in trades.items():
        if not isinstance(raw, Mapping):
            continue
        ets_id = _ets_id(raw.get("ets_id"), raw.get("identifier") or key)
        if not ets_id:
            continue
        yield raw, ets_id, parent_ets_id
        nested = raw.get("trades")
        if isinstance(nested, Mapping):
            yield from _walk_trades(nested, ets_id)


def _trades_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Trade]:
    rows = session.scalars(
        select(Trade)
        .where(Trade.installation_id == installation_id)
        .options(selectinload(Trade.versions))
    ).all()
    return {row.ets_id: row for row in rows}


def _devices_by_ets_id(session: Session, installation_id: UUID) -> dict[str, Device]:
    rows = session.scalars(
        select(Device).where(Device.installation_id == installation_id)
    ).all()
    return {row.ets_id: row for row in rows}


def _trade_devices_by_pair(
    session: Session, installation_id: UUID
) -> dict[tuple[UUID, UUID], list[TradeDevice]]:
    rows = session.scalars(
        select(TradeDevice)
        .join(Trade, Trade.id == TradeDevice.trade_id)
        .where(Trade.installation_id == installation_id)
    ).all()
    grouped: dict[tuple[UUID, UUID], list[TradeDevice]] = {}
    for row in rows:
        grouped.setdefault((row.trade_id, row.device_id), []).append(row)
    return grouped


def _ets_id(explicit: object, identifier: object) -> str | None:
    value = _optional_str(explicit)
    if value:
        return value.rsplit("_", 1)[-1] or None
    ident = _optional_str(identifier)
    if not ident:
        return None
    return ident.rsplit("_", 1)[-1] or None


def _optional_str(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    return str(raw)


def _completion_status(raw: object) -> str | None:
    value = _optional_str(raw)
    if value is None:
        return None
    if value not in COMPLETION_STATUS_VALUES:
        raise KnxprojImportError(f"unsupported completion status {value!r}")
    return value


def _last_modified(raw: object, fallback: datetime) -> datetime:
    text = _optional_str(raw)
    parsed: datetime | None = None
    if text is not None:
        try:
            parsed = parse_ets_datetime(text)
        except (TypeError, ValueError):
            parsed = None
    if parsed is None:
        parsed = fallback
    return _aware_utc(parsed)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
