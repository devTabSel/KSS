from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kss.models.trade import Trade, TradeDevice, TradeVersion
from kss.services.trades import upsert_trades_from_project
from tests.helpers import persist_device, persist_installation, persist_trade

FALLBACK = datetime(2026, 8, 7, 8, 28, 38, tzinfo=UTC)

TRADE_PROJECT = {
    "trades": {
        "T-14": {
            "name": "BUS",
            "identifier": "P-040E-0_T-14",
            "ets_id": "T-14",
            "number": None,
            "description": "KNX Bus",
            "comment": None,
            "completion_status": "Accepted",
            "last_modified": None,
            "devices": [],
            "trades": {
                "T-46": {
                    "name": "BUS_DPS1280",
                    "identifier": "P-040E-0_T-46",
                    "ets_id": "T-46",
                    "number": None,
                    "description": "Enertex Dual Power Supply 1280",
                    "comment": None,
                    "completion_status": "Accepted",
                    "last_modified": None,
                    "devices": ["DI-1"],
                    "trades": {},
                }
            },
        }
    }
}


def test_upsert_nested_trade_and_device_edge(session: Session) -> None:
    installation = persist_installation(session, last_modified=FALLBACK)
    device = persist_device(session, installation, ets_id="DI-1")
    upsert_trades_from_project(session, installation, TRADE_PROJECT, FALLBACK)

    trades = {row.ets_id: row for row in session.scalars(select(Trade)).all()}
    assert set(trades) == {"T-14", "T-46"}
    parent = max(trades["T-14"].versions, key=lambda item: item.last_modified)
    child = max(trades["T-46"].versions, key=lambda item: item.last_modified)
    assert parent.name == "BUS"
    assert parent.parent_trade_id is None
    assert parent.completion_status == "Accepted"
    assert child.name == "BUS_DPS1280"
    assert child.parent_trade_id == trades["T-14"].id

    edge = session.scalars(select(TradeDevice)).one()
    assert edge.trade_id == trades["T-46"].id
    assert edge.device_id == device.id
    assert edge.linked is True

    upsert_trades_from_project(session, installation, TRADE_PROJECT, FALLBACK)
    assert session.scalar(select(func.count()).select_from(TradeVersion)) == 2
    assert session.scalar(select(func.count()).select_from(TradeDevice)) == 1


def test_missing_trades_key_writes_nothing(session: Session) -> None:
    installation = persist_installation(session)
    persist_trade(session, installation, ets_id="T-99")
    upsert_trades_from_project(session, installation, {}, FALLBACK)
    assert session.scalar(select(func.count()).select_from(Trade)) == 1
    assert session.scalars(select(Trade)).one().ets_id == "T-99"
