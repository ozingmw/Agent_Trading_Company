from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SQLiteStore:
    db_path: Path

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA foreign_keys=ON;")
            self._migrate(connection)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _migrate(self, connection: sqlite3.Connection) -> None:
        current_version = connection.execute("PRAGMA user_version;").fetchone()[0]
        if current_version < 1:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    position_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    symbol TEXT,
                    exchange TEXT,
                    qty REAL,
                    avg_price REAL,
                    market_value REAL,
                    updated_at TEXT
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    symbol TEXT,
                    exchange TEXT,
                    side TEXT,
                    qty REAL,
                    price REAL,
                    order_type TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    raw_response TEXT
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pnl (
                    pnl_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    date TEXT,
                    realized REAL,
                    unrealized REAL,
                    total REAL
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS data_registry (
                    data_id TEXT PRIMARY KEY,
                    source TEXT,
                    symbol TEXT,
                    start_ts TEXT,
                    end_ts TEXT,
                    path TEXT,
                    format TEXT,
                    checksum TEXT,
                    created_at TEXT
                );
                """
            )
            connection.execute("PRAGMA user_version=1;")

    def save_order(self, order: dict[str, Any]) -> None:
        payload = json.dumps(order)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO orders (
                    order_id, agent_id, symbol, exchange, side, qty, price, order_type,
                    status, created_at, updated_at, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    order.get("order_id"),
                    order.get("agent_id"),
                    order.get("symbol"),
                    order.get("exchange"),
                    order.get("side"),
                    order.get("qty"),
                    order.get("price"),
                    order.get("order_type"),
                    order.get("status"),
                    order.get("created_at"),
                    order.get("updated_at"),
                    payload,
                ),
            )

    def get_orders(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        query = "SELECT raw_response FROM orders"
        params: list[Any] = []
        if filters:
            clauses = []
            for key, value in filters.items():
                clauses.append(f"{key} = ?")
                params.append(value)
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_position(self, position: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO positions (
                    position_id, agent_id, symbol, exchange, qty, avg_price, market_value, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    position.get("position_id"),
                    position.get("agent_id"),
                    position.get("symbol"),
                    position.get("exchange"),
                    position.get("qty"),
                    position.get("avg_price"),
                    position.get("market_value"),
                    position.get("updated_at"),
                ),
            )

    def get_positions(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT position_id, agent_id, symbol, exchange, qty, avg_price, market_value, updated_at
                FROM positions
                """
            ).fetchall()
        return [
            {
                "position_id": row[0],
                "agent_id": row[1],
                "symbol": row[2],
                "exchange": row[3],
                "qty": row[4],
                "avg_price": row[5],
                "market_value": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]

    def save_pnl(self, pnl: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO pnl (
                    pnl_id, agent_id, date, realized, unrealized, total
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    pnl.get("pnl_id"),
                    pnl.get("agent_id"),
                    pnl.get("date"),
                    pnl.get("realized"),
                    pnl.get("unrealized"),
                    pnl.get("total"),
                ),
            )

    def get_pnl_window(self, n: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT pnl_id, agent_id, date, realized, unrealized, total
                FROM pnl
                ORDER BY date DESC
                LIMIT ?
                """,
                (n,),
            ).fetchall()
        return [
            {
                "pnl_id": row[0],
                "agent_id": row[1],
                "date": row[2],
                "realized": row[3],
                "unrealized": row[4],
                "total": row[5],
            }
            for row in rows
        ]

    def register_data(self, source: str, path: str, metadata: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO data_registry (
                    data_id, source, symbol, start_ts, end_ts, path, format, checksum, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    metadata.get("data_id"),
                    source,
                    metadata.get("symbol"),
                    metadata.get("start_ts"),
                    metadata.get("end_ts"),
                    path,
                    metadata.get("format"),
                    metadata.get("checksum"),
                    metadata.get("created_at"),
                ),
            )

    def get_latest_data(self, source: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT data_id, source, symbol, start_ts, end_ts, path, format, checksum, created_at
                FROM data_registry
                WHERE source = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (source,),
            ).fetchone()
        if row is None:
            return None
        return {
            "data_id": row[0],
            "source": row[1],
            "symbol": row[2],
            "start_ts": row[3],
            "end_ts": row[4],
            "path": row[5],
            "format": row[6],
            "checksum": row[7],
            "created_at": row[8],
        }
