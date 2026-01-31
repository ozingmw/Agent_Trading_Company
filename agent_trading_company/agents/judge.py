from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent_trading_company.core.directives import compute_directive_hash
from agent_trading_company.io.atomic_writer import atomic_write


@dataclass(frozen=True)
class PortfolioSnapshot:
    created_at: datetime
    pnl_total: float


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


def _load_active_agents(registry_path: Path) -> list[str]:
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or []
    return [entry["agent_id"] for entry in data if entry.get("enabled", True)]


def _load_portfolio_snapshots(limit: int = 20) -> list[PortfolioSnapshot]:
    portfolio_dir = Path("artifacts/portfolio")
    if not portfolio_dir.exists():
        return []
    files = sorted(portfolio_dir.glob("*.md"))[-limit:]
    snapshots = []
    for path in files:
        fm = _parse_front_matter(path)
        created_at = datetime.fromisoformat(str(fm.get("created_at")).replace("Z", "+00:00"))
        pnl_total = float(fm.get("payload", {}).get("pnl_total", 0))
        snapshots.append(PortfolioSnapshot(created_at=created_at, pnl_total=pnl_total))
    return snapshots


def _score_quant(snapshots: list[PortfolioSnapshot]) -> float:
    if len(snapshots) < 2:
        return 0.0
    returns = [snapshots[i].pnl_total - snapshots[i - 1].pnl_total for i in range(1, len(snapshots))]
    mean_val = statistics.mean(returns)
    std_val = statistics.pstdev(returns) + 1e-9
    return mean_val / std_val


def _score_qual() -> float:
    return statistics.mean([3, 3, 3])


def _prompt_template(agent_id: str, directive_hash: str) -> str:
    return (
        "---\n"
        f"agent_id: \"{agent_id}\"\n"
        f"updated_at: \"{_iso_ts(_now_utc())}\"\n"
        "score: 0\n"
        f"directive_hash: \"{directive_hash}\"\n"
        "---\n"
        "## Judge Feedback\n"
    )


def _ensure_prompt(agent_id: str, directive_hash: str) -> Path:
    prompt_path = Path("prompts") / f"{agent_id}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    if not prompt_path.exists():
        atomic_write(prompt_path, _prompt_template(agent_id, directive_hash))
    return prompt_path


def _append_prompt_history(agent_id: str, content: str) -> Path:
    history_dir = Path("prompts/history") / agent_id
    history_dir.mkdir(parents=True, exist_ok=True)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    timestamp = _now_utc().strftime("%Y%m%d_%H%M%SZ")
    history_path = history_dir / f"{timestamp}_{content_hash}.md"
    atomic_write(history_path, content)
    return history_path


def _update_prompt(prompt_path: Path, directive_hash: str, score: float) -> Path:
    content = prompt_path.read_text(encoding="utf-8")
    if "## Judge Feedback" not in content:
        content += "\n## Judge Feedback\n"
    content += f"- {_iso_ts(_now_utc())}: score={score:.2f}\n"
    new_content = content.replace("directive_hash: ", f"directive_hash: \"{directive_hash}\"\n", 1)
    atomic_write(prompt_path, new_content)
    return _append_prompt_history(prompt_path.stem, new_content)


def run(artifact_path: str, directives: dict, store: object) -> str:
    now = _now_utc()
    directive_hash = compute_directive_hash(Path("directives/admin_directives.md").read_text(encoding="utf-8"))

    snapshots = _load_portfolio_snapshots(20)
    score = _score_quant(snapshots) if snapshots else _score_qual()

    active_agents = _load_active_agents(Path("agent_trading_company/orchestrator/registry.yml"))
    scores = {agent_id: score for agent_id in active_agents if agent_id.startswith("analyst")}
    leaderboard_top = next(iter(scores.keys()), "")

    references = []
    for agent_id in scores.keys():
        prompt_path = _ensure_prompt(agent_id, directive_hash)
        history_path = _update_prompt(prompt_path, directive_hash, score)
        references.append(str(history_path))

    output_path = Path("artifacts/leaderboard") / f"{now.strftime('%Y%m%d_%H%M%SZ')}_judge-1_leaderboard_j1.md"
    front_matter = {
        "artifact_id": f"j1-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "judge-1",
        "role": "judge",
        "created_at": _iso_ts(now),
        "inputs": [artifact_path],
        "outputs": [str(output_path)],
        "directive_hash": directive_hash,
        "references": references,
        "payload": {
            "leaderboard_top": leaderboard_top,
            "scores": scores,
            "rationale": None,
        },
        "artifact_kind": "leaderboard",
        "status": "completed",
    }

    content = (
        f"---\n{yaml.safe_dump(front_matter, sort_keys=False).strip()}\n---\n"
        f"Leaderboard updated. Top agent: {leaderboard_top} score={score:.2f}\n"
    )
    atomic_write(output_path, content)
    return str(output_path)
