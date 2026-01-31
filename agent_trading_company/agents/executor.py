from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_trading_company.core.directives import compute_directive_hash
from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.kis.client import KISClient
from agent_trading_company.kis.errors import UnsupportedMarket


@dataclass(frozen=True)
class AnalystSignal:
    symbol: str
    exchange: str
    side: str
    order_type: str
    limit_price: float | None
    size_hint: float


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_ts(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_front_matter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing front matter")
    idx = 1
    fm_lines: list[str] = []
    while idx < len(lines) and lines[idx].strip() != "---":
        fm_lines.append(lines[idx])
        idx += 1
    return yaml.safe_load("\n".join(fm_lines)) or {}


def _parse_signal(path: Path) -> AnalystSignal:
    fm = _parse_front_matter(path)
    payload = fm.get("payload", {})
    return AnalystSignal(
        symbol=str(payload.get("symbol")),
        exchange=str(payload.get("exchange")),
        side=str(payload.get("side")),
        order_type=str(payload.get("order_type")),
        limit_price=payload.get("limit_price"),
        size_hint=float(payload.get("size_hint", 1)),
    )


def _parse_critic(path: Path) -> dict:
    fm = _parse_front_matter(path)
    payload = fm.get("payload", {})
    return {
        "recommendation": str(payload.get("recommendation")),
    }


def run(artifact_path: str, directives: dict, store: object) -> str:
    now = _now_utc()
    analyst_path = Path(artifact_path)
    critic_path = Path(str(directives.get("critic_artifact", "")))
    signal = _parse_signal(analyst_path)
    critic = _parse_critic(critic_path) if critic_path.exists() else {"recommendation": ""}

    directive_hash = compute_directive_hash(Path("directives/admin_directives.md").read_text(encoding="utf-8"))
    output_path = Path("artifacts/executor") / f"{now.strftime('%Y%m%d_%H%M%SZ')}_executor-1_executor_e1.md"

    client = KISClient.from_env()
    try:
        response = client.place_order(
            directives.get("market_universe", "KRX"),
            signal.exchange,
            signal.symbol,
            signal.side,
            int(signal.size_hint),
            signal.limit_price,
        )
        order_id = str(response.get("output", {}).get("ODNO", ""))
        status = "SUBMITTED"
    except UnsupportedMarket:
        order_id = ""
        status = "ERROR"

    front_matter = {
        "artifact_id": f"e1-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "executor-1",
        "role": "executor",
        "created_at": _iso_ts(now),
        "inputs": [str(analyst_path)] + ([str(critic_path)] if critic_path.exists() else []),
        "outputs": [str(output_path)],
        "directive_hash": directive_hash,
        "payload": {
            "order_id": order_id,
            "status": status,
            "symbol": signal.symbol,
            "critic_recommendation": critic.get("recommendation", ""),
        },
        "status": "completed",
    }

    content = (
        f"---\n{yaml.safe_dump(front_matter, sort_keys=False).strip()}\n---\n"
        f"Order submitted: order_id={order_id} status={status} symbol={signal.symbol}\n"
    )
    atomic_write(output_path, content)
    return str(output_path)
