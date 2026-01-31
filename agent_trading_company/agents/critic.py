from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_trading_company.core.directives import compute_directive_hash
from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.llm.router import get_router


@dataclass(frozen=True)
class AnalystSignal:
    symbol: str
    exchange: str
    confidence: float


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_ts(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_signal(path: Path) -> AnalystSignal:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing front matter")
    idx = 1
    fm_lines: list[str] = []
    while idx < len(lines) and lines[idx].strip() != "---":
        fm_lines.append(lines[idx])
        idx += 1
    fm = yaml.safe_load("\n".join(fm_lines)) or {}
    payload = fm.get("payload", {})
    return AnalystSignal(
        symbol=str(payload.get("symbol")),
        exchange=str(payload.get("exchange")),
        confidence=float(payload.get("confidence", 0)),
    )


def run(artifact_path: str, directives: dict, store: object) -> str:
    now = _now_utc()
    analyst_path = Path(artifact_path)
    signal = _parse_signal(analyst_path)

    router = get_router()
    result = router.invoke("critic_review", {"confidence": signal.confidence})
    recommendation = str(result.get("recommendation", "APPROVE"))
    directive_hash = compute_directive_hash(Path("directives/admin_directives.md").read_text(encoding="utf-8"))
    output_path = Path("artifacts/critic") / f"{now.strftime('%Y%m%d_%H%M%SZ')}_critic-1_critic_cr1.md"
    front_matter = {
        "artifact_id": f"cr1-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "critic-1",
        "role": "critic",
        "created_at": _iso_ts(now),
        "inputs": [artifact_path],
        "outputs": [str(output_path)],
        "directive_hash": directive_hash,
        "payload": {
            "recommendation": recommendation,
            "adjustment": None,
            "notes": result.get("notes", "No issues detected"),
        },
        "status": "completed",
    }
    content = (
        f"---\n{yaml.safe_dump(front_matter, sort_keys=False).strip()}\n---\n"
        f"Critic {recommendation.lower()}s the signal.\n"
    )
    atomic_write(output_path, content)
    return str(output_path)
