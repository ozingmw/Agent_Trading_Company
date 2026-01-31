from __future__ import annotations

import os
from pathlib import Path


def get_base_dir() -> Path:
    base_dir = os.getenv("ATC_BASE_DIR")
    if base_dir:
        return Path(base_dir).expanduser().resolve()
    return Path.cwd().resolve()


def get_state_dir() -> Path:
    return get_base_dir() / "state"


def ensure_state_dir() -> Path:
    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_db_path() -> Path:
    return ensure_state_dir() / "agent_state.sqlite"
