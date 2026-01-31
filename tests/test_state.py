from __future__ import annotations

from pathlib import Path

from agent_trading_company.core.paths import ensure_state_dir, get_db_path
from agent_trading_company.storage.state import init_state_store


def test_state_dir_helpers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ATC_BASE_DIR", str(tmp_path))
    state_dir = ensure_state_dir()
    assert state_dir.exists()
    assert state_dir.name == "state"
    assert get_db_path().name == "agent_state.sqlite"


def test_init_state_store_uses_default_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ATC_BASE_DIR", str(tmp_path))
    store = init_state_store()
    assert store.db_path == get_db_path()
