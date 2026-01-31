from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_trading_company.core.directives import compute_directive_hash
from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.kis.client import KISClient
from agent_trading_company.storage.store import Store


@dataclass(frozen=True)
class ExecutionResult:
    symbol: str
    status: str


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


def _parse_execution(path: Path) -> ExecutionResult:
    fm = _parse_front_matter(path)
    payload = fm.get("payload", {})
    return ExecutionResult(symbol=str(payload.get("symbol")), status=str(payload.get("status")))


def _load_initial_cash(store: Store, client: KISClient) -> float:
    record = store.get_latest_data("initial_cash")
    if record is not None:
        return float(record.get("cash", 0))
    balance = client.get_balance("KRX", "KRX", "KRW")
    cash = float(balance.get("output2", {}).get("dnca_tot_amt", 0)) if isinstance(balance, dict) else 0.0
    store.register_data("initial_cash", "", {"data_id": "initial", "cash": cash, "created_at": _iso_ts(_now_utc())})
    return cash


def run(artifact_path: str, directives: dict, store: Store) -> str:
    now = _now_utc()
    execution_path = Path(artifact_path)
    execution = _parse_execution(execution_path)

    client = KISClient.from_env()
    initial_cash = _load_initial_cash(store, client)

    positions = store.get_positions()
    market_value = sum(float(pos.get("market_value", 0)) for pos in positions)
    cash = initial_cash
    pnl_total = (market_value + cash) - initial_cash

    directive_hash = compute_directive_hash(Path("directives/admin_directives.md").read_text(encoding="utf-8"))
    output_path = Path("artifacts/portfolio") / f"{now.strftime('%Y%m%d_%H%M%SZ')}_portfolio-1_portfolio_p1.md"
    front_matter = {
        "artifact_id": f"p1-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "portfolio-1",
        "role": "portfolio",
        "created_at": _iso_ts(now),
        "inputs": [str(execution_path)],
        "outputs": [str(output_path)],
        "directive_hash": directive_hash,
        "payload": {
            "cash": cash,
            "positions_count": len(positions),
            "pnl_total": pnl_total,
        },
        "status": "completed",
    }

    content = (
        f"---\n{yaml.safe_dump(front_matter, sort_keys=False).strip()}\n---\n"
        "Portfolio snapshot updated.\n"
    )
    atomic_write(output_path, content)
    return str(output_path)
