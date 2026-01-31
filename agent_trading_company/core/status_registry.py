from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.io.file_lock import file_lock


@dataclass(frozen=True)
class StatusEntry:
    agent_id: str
    status: str
    last_heartbeat: str
    current_task: str
    last_artifact: str


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n")


def compute_status_hash(content: str) -> str:
    normalized = _normalize_text(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _status_front_matter(entry: StatusEntry) -> dict[str, Any]:
    return {
        "agent_id": entry.agent_id,
        "status": entry.status,
        "last_heartbeat": entry.last_heartbeat,
        "current_task": entry.current_task,
        "last_artifact": entry.last_artifact,
    }


def _render_status(entry: StatusEntry) -> str:
    front = yaml.safe_dump(_status_front_matter(entry), sort_keys=False).strip()
    return f"---\n{front}\n---\n"


def update_status(path: Path, entry: StatusEntry) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    content = _render_status(entry)
    with file_lock(lock_path):
        atomic_write(path, content)
    return compute_status_hash(content)


def now_utc() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
