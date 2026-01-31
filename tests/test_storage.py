from __future__ import annotations

from pathlib import Path

from agent_trading_company.storage.sqlite_store import SQLiteStore


def test_sqlite_store_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "agent_state.sqlite"
    store = SQLiteStore(db_path=db_path)

    with store._connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }

    assert "positions" in tables
    assert "orders" in tables
    assert "pnl" in tables
    assert "data_registry" in tables


def test_sqlite_store_order_roundtrip(tmp_path: Path) -> None:
    store = SQLiteStore(db_path=tmp_path / "state" / "agent_state.sqlite")
    store.save_order(
        {
            "order_id": "o1",
            "agent_id": "executor-1",
            "symbol": "AAPL",
            "exchange": "NASD",
            "side": "BUY",
            "qty": 1,
            "price": 100.0,
            "order_type": "LIMIT",
            "status": "SUBMITTED",
            "created_at": "2026-01-30T00:00:00Z",
            "updated_at": "2026-01-30T00:00:00Z",
        }
    )
    rows = store.get_orders({"order_id": "o1"})
    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"


def test_sqlite_store_positions_and_pnl(tmp_path: Path) -> None:
    store = SQLiteStore(db_path=tmp_path / "state" / "agent_state.sqlite")
    store.save_position(
        {
            "position_id": "p1",
            "agent_id": "portfolio-1",
            "symbol": "AAPL",
            "exchange": "NASD",
            "qty": 1.0,
            "avg_price": 100.0,
            "market_value": 101.0,
            "updated_at": "2026-01-30T00:00:00Z",
        }
    )
    store.save_pnl(
        {
            "pnl_id": "pnl-1",
            "agent_id": "portfolio-1",
            "date": "2026-01-30",
            "realized": 0.0,
            "unrealized": 1.0,
            "total": 1.0,
        }
    )

    positions = store.get_positions()
    pnl_rows = store.get_pnl_window(1)

    assert positions[0]["symbol"] == "AAPL"
    assert pnl_rows[0]["total"] == 1.0


def test_sqlite_store_register_data(tmp_path: Path) -> None:
    store = SQLiteStore(db_path=tmp_path / "state" / "agent_state.sqlite")
    store.register_data(
        "kis",
        "data/raw/20260130/kis_quotes.jsonl",
        {
            "data_id": "d1",
            "symbol": "AAPL",
            "start_ts": "2026-01-30T00:00:00Z",
            "end_ts": "2026-01-30T00:01:00Z",
            "format": "jsonl",
            "checksum": "abc",
            "created_at": "2026-01-30T00:02:00Z",
        },
    )
    latest = store.get_latest_data("kis")
    assert latest is not None
    assert latest["data_id"] == "d1"
