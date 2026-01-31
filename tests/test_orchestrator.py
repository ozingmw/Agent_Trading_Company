from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_trading_company.orchestrator.emit_tick import build_tick_content
from agent_trading_company.orchestrator.runner import _parse_front_matter, _resolve_conflict, route_artifact


def _write_artifact(path: Path, front: dict, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    front_text = yaml.safe_dump(front, sort_keys=False).strip()
    path.write_text(f"---\n{front_text}\n---\n{body}", encoding="utf-8")


def test_emit_tick_builds_valid_front_matter() -> None:
    now = datetime(2026, 1, 30, 12, 0, 0, tzinfo=timezone.utc)
    content = build_tick_content(now, "interval")
    assert "role: \"orchestrator\"" in content
    assert "tick_type" in content


def test_route_from_collector_to_analyst(tmp_path: Path) -> None:
    artifact = tmp_path / "collector.md"
    _write_artifact(
        artifact,
        {
            "artifact_id": "c1",
            "agent_id": "collector-1",
            "role": "collector",
            "created_at": "2026-01-30T00:00:00Z",
            "inputs": [],
            "outputs": ["data/raw/sample.jsonl"],
            "directive_hash": "hash",
            "payload": {"sources": [], "universe": "KRX", "counts": {}, "outputs_by_source": {}},
            "status": "completed",
        },
    )

    registry = [
        type("Spec", (), {"role": "analyst", "enabled": True})(),
    ]

    targets = route_artifact(artifact, registry)
    assert len(targets) == 1


def test_conflict_resolution_prefers_higher_score(tmp_path: Path, monkeypatch) -> None:
    analyst_dir = tmp_path / "artifacts" / "analyst"
    monkeypatch.chdir(tmp_path)

    first = analyst_dir / "a1.md"
    second = analyst_dir / "a2.md"

    _write_artifact(
        first,
        {
            "artifact_id": "a1",
            "agent_id": "analyst-1",
            "role": "analyst",
            "created_at": "2026-01-30T12:00:00Z",
            "inputs": [],
            "outputs": [],
            "directive_hash": "hash",
            "payload": {
                "symbol": "AAPL",
                "exchange": "NASD",
                "side": "BUY",
                "order_type": "LIMIT",
                "limit_price": 100.0,
                "size_hint": 1.0,
                "confidence": 0.2,
            },
            "status": "completed",
        },
    )

    _write_artifact(
        second,
        {
            "artifact_id": "a2",
            "agent_id": "analyst-2",
            "role": "analyst",
            "created_at": "2026-01-30T12:05:00Z",
            "inputs": [],
            "outputs": [],
            "directive_hash": "hash",
            "payload": {
                "symbol": "AAPL",
                "exchange": "NASD",
                "side": "SELL",
                "order_type": "LIMIT",
                "limit_price": 101.0,
                "size_hint": 1.0,
                "confidence": 0.9,
            },
            "status": "completed",
        },
    )

    selected = _resolve_conflict([first, second])
    assert selected == second


def test_parse_front_matter_handles_yaml(tmp_path: Path) -> None:
    file_path = tmp_path / "artifact.md"
    _write_artifact(
        file_path,
        {
            "artifact_id": "a1",
            "agent_id": "collector-1",
            "role": "collector",
            "created_at": "2026-01-30T00:00:00Z",
            "inputs": [],
            "outputs": [],
            "directive_hash": "hash",
            "payload": {"sources": [], "universe": "KRX", "counts": {}, "outputs_by_source": {}},
            "status": "completed",
        },
    )
    fm = _parse_front_matter(file_path)
    assert fm["role"] == "collector"
