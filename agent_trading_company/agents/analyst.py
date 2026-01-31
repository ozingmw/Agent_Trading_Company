from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_trading_company.core.directives import compute_directive_hash
from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.llm.router import get_router


@dataclass(frozen=True)
class QuoteRecord:
    ts: str
    source: str
    symbol: str
    exchange: str
    price: float


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_ts(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_collector_payload(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    idx = 1
    fm_lines: list[str] = []
    while idx < len(lines) and lines[idx].strip() != "---":
        fm_lines.append(lines[idx])
        idx += 1
    fm = yaml.safe_load("\n".join(fm_lines)) or {}
    return fm.get("payload", {}) or {}


def _load_last_two_quotes(path: Path) -> list[QuoteRecord]:
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-2:] if len(lines) >= 2 else lines
    records = []
    for line in tail:
        data = json.loads(line)
        records.append(
            QuoteRecord(
                ts=str(data.get("ts")),
                source=str(data.get("source")),
                symbol=str(data.get("symbol")),
                exchange=str(data.get("exchange")),
                price=float(data.get("price")),
            )
        )
    return records


def run(artifact_path: str, directives: dict, store: object) -> str:
    now = _now_utc()
    collector_path = Path(artifact_path)
    payload = _parse_collector_payload(collector_path)
    kis_path = Path(payload.get("outputs_by_source", {}).get("kis", ""))
    if not kis_path.exists():
        raise ValueError("Missing KIS data source in collector payload")

    quotes = _load_last_two_quotes(kis_path)
    if not quotes:
        raise ValueError("No quotes found in KIS JSONL")

    router = get_router()
    skill_result = router.invoke(
        "analyst_signal",
        {
            "quotes": [quote.__dict__ for quote in quotes],
            "default_order_size": directives.get("default_order_size", 1),
        },
    )
    side = str(skill_result.get("side", "BUY"))
    confidence = float(skill_result.get("confidence", 0.5))

    directive_hash = compute_directive_hash(Path("directives/admin_directives.md").read_text(encoding="utf-8"))
    output_path = Path("artifacts/analyst") / f"{now.strftime('%Y%m%d_%H%M%SZ')}_analyst-1_analyst_a1.md"
    front_matter = {
        "artifact_id": f"a1-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "analyst-1",
        "role": "analyst",
        "created_at": _iso_ts(now),
        "inputs": [artifact_path],
        "outputs": [str(output_path)],
        "directive_hash": directive_hash,
        "payload": {
            "symbol": quotes[-1].symbol,
            "exchange": quotes[-1].exchange,
            "side": side,
            "order_type": skill_result.get("order_type", "LIMIT"),
            "limit_price": skill_result.get("limit_price", quotes[-1].price),
            "size_hint": float(skill_result.get("size_hint", directives.get("default_order_size", 1))),
            "confidence": confidence,
        },
        "status": "completed",
    }

    content = (
        f"---\n{yaml.safe_dump(front_matter, sort_keys=False).strip()}\n---\n"
        f"Signal: {side} {quotes[-1].symbol} confidence={confidence}\n"
    )
    atomic_write(output_path, content)
    return str(output_path)
