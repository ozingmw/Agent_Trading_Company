from __future__ import annotations

from pathlib import Path

from agent_trading_company.core.paths import get_db_path
from agent_trading_company.storage.sqlite_store import SQLiteStore


def init_state_store(db_path: Path | None = None) -> SQLiteStore:
    return SQLiteStore(db_path=db_path or get_db_path())
