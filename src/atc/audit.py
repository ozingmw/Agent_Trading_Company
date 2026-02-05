from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    cycle_id TEXT,
                    payload TEXT,
                    prompt TEXT,
                    response TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS critic_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    cycle_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    notes TEXT NOT NULL
                )
                """
            )

    def _sanitize_payload(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == "MarketDataReady":
            summary = payload.get("summary", {})
            return {
                "summary": {
                    "quotes_count": len(summary.get("quotes", {})),
                    "news_count": len(summary.get("news", [])),
                    "social_count": len(summary.get("social", [])),
                    "notes": summary.get("notes", []),
                }
            }
        if event_type in {"OrderRequest", "OrderUpdate"}:
            orders = payload.get("orders") or payload.get("results") or []
            return {"count": len(orders)}
        return payload

    def log_event(
        self,
        agent: str,
        event_type: str,
        payload: Dict[str, Any],
        cycle_id: Optional[str] = None,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
    ) -> None:
        safe_payload = self._sanitize_payload(event_type, payload)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO audit_events (ts, agent, event_type, cycle_id, payload, prompt, response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    agent,
                    event_type,
                    cycle_id,
                    json.dumps(safe_payload, ensure_ascii=True),
                    prompt,
                    response,
                ),
            )

    def log_feedback(self, agent: str, cycle_id: str, score: float, notes: str) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO critic_feedback (ts, agent, cycle_id, score, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    agent,
                    cycle_id,
                    score,
                    notes,
                ),
            )

    def latest_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT ts, agent, event_type, cycle_id, payload
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        results = []
        for ts, agent, event_type, cycle_id, payload in rows:
            results.append(
                {
                    "ts": ts,
                    "agent": agent,
                    "event_type": event_type,
                    "cycle_id": cycle_id,
                    "payload": json.loads(payload) if payload else {},
                }
            )
        return results
