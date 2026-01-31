from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from agent_trading_company.core.directives import compute_directive_hash, load_directives
from agent_trading_company.core.status_registry import StatusEntry, now_utc, update_status
from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.io.file_lock import file_lock
from agent_trading_company.io.watcher import ArtifactReadyHandler, start_watcher
from agent_trading_company.storage.state import init_state_store


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    role: str
    handler: str
    enabled: bool


def _load_registry(path: Path) -> list[AgentSpec]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    specs = []
    for entry in data:
        specs.append(
            AgentSpec(
                agent_id=str(entry["agent_id"]),
                role=str(entry["role"]),
                handler=str(entry["handler"]),
                enabled=bool(entry.get("enabled", True)),
            )
        )
    return specs


def _import_handler(handler: str) -> Callable[[str, dict, object], str]:
    module_name, func_name = handler.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def _processed_state_path() -> Path:
    return Path("state/processed_artifacts.json")


def _read_processed() -> dict[str, str]:
    path = _processed_state_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("processed", {})


def _write_processed(processed: dict[str, str]) -> None:
    path = _processed_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"processed": processed}
    atomic_write(path, json.dumps(payload, indent=2))


def _mark_processed(artifact_id: str) -> None:
    lock_path = _processed_state_path().with_suffix(".json.lock")
    with file_lock(lock_path):
        processed = _read_processed()
        processed[artifact_id] = now_utc()
        _write_processed(processed)


def _already_processed(artifact_id: str) -> bool:
    return artifact_id in _read_processed()


def _parse_front_matter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    idx = 1
    fm_lines: list[str] = []
    while idx < len(lines) and lines[idx].strip() != "---":
        fm_lines.append(lines[idx])
        idx += 1
    return yaml.safe_load("\n".join(fm_lines)) or {}


def _candidate_score(artifact_path: Path, judge_scores: dict[str, float]) -> float:
    fm = _parse_front_matter(artifact_path)
    payload = fm.get("payload", {})
    confidence = float(payload.get("confidence", 0))
    agent_id = fm.get("agent_id", "")
    judge_score = float(judge_scores.get(agent_id, 1.0))
    return judge_score * confidence


def _load_latest_leaderboard_scores() -> dict[str, float]:
    leaderboard_dir = Path("artifacts/leaderboard")
    if not leaderboard_dir.exists():
        return {}
    files = sorted(leaderboard_dir.glob("*.md"))
    if not files:
        return {}
    latest = files[-1]
    fm = _parse_front_matter(latest)
    payload = fm.get("payload", {})
    return payload.get("scores", {}) or {}


def _resolve_conflict(candidate_paths: list[Path]) -> Path:
    scores = _load_latest_leaderboard_scores()
    scored = sorted(
        candidate_paths,
        key=lambda path: _candidate_score(path, scores),
        reverse=True,
    )
    return scored[0]


def _status_path(agent_id: str) -> Path:
    return Path("artifacts/status") / f"{agent_id}.md"


def _update_status(agent_id: str, status: str, current_task: str, last_artifact: str) -> None:
    entry = StatusEntry(
        agent_id=agent_id,
        status=status,
        last_heartbeat=now_utc(),
        current_task=current_task,
        last_artifact=last_artifact,
    )
    update_status(_status_path(agent_id), entry)


def route_artifact(path: Path, registry: list[AgentSpec]) -> list[AgentSpec]:
    fm = _parse_front_matter(path)
    role = fm.get("role")
    if role == "collector":
        return [spec for spec in registry if spec.role == "analyst" and spec.enabled]
    if role == "analyst":
        return [spec for spec in registry if spec.role == "critic" and spec.enabled]
    if role == "critic":
        return [spec for spec in registry if spec.role == "executor" and spec.enabled]
    if role == "executor":
        return [spec for spec in registry if spec.role == "portfolio" and spec.enabled]
    if role == "portfolio":
        return [spec for spec in registry if spec.role == "judge" and spec.enabled]
    if role == "orchestrator":
        payload = fm.get("payload", {})
        if payload.get("tick_type") in ("startup", "interval"):
            return [spec for spec in registry if spec.role == "collector" and spec.enabled]
    return []


def _scan_conflicts(artifact_path: Path) -> Path:
    fm = _parse_front_matter(artifact_path)
    payload = fm.get("payload", {})
    symbol = payload.get("symbol")
    exchange = payload.get("exchange")
    created_at = fm.get("created_at")
    if not symbol or not exchange or not created_at:
        return artifact_path

    window = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    cutoff = window.timestamp() - 600
    candidates = []
    for candidate in Path("artifacts/analyst").glob("*.md"):
        cfm = _parse_front_matter(candidate)
        cpayload = cfm.get("payload", {})
        if cpayload.get("symbol") != symbol or cpayload.get("exchange") != exchange:
            continue
        cts = cfm.get("created_at")
        if not cts:
            continue
        ts_val = datetime.fromisoformat(cts.replace("Z", "+00:00")).timestamp()
        if ts_val >= cutoff:
            candidates.append(candidate)
    if not candidates:
        return artifact_path
    return _resolve_conflict(candidates)


def run_handler(handler: Callable[[str, dict, object], str], artifact_path: Path, directives: dict, store: object) -> str:
    return handler(str(artifact_path), directives, store)


def handle_artifact(artifact_path: Path, registry: list[AgentSpec]) -> None:
    fm = _parse_front_matter(artifact_path)
    artifact_id = fm.get("artifact_id")
    if artifact_id and _already_processed(artifact_id):
        return

    selected_path = artifact_path
    if fm.get("role") == "analyst":
        selected_path = _scan_conflicts(artifact_path)

    directives, directive_hash = load_directives(Path("directives/admin_directives.md"))
    directives_data = directives.__dict__.copy()
    directives_data["directive_hash"] = directive_hash

    store = init_state_store()
    targets = route_artifact(selected_path, registry)
    for target in targets:
        handler = _import_handler(target.handler)
        _update_status(target.agent_id, "working", target.role, str(selected_path))
        _ = run_handler(handler, selected_path, directives_data, store)
        _update_status(target.agent_id, "completed", target.role, str(selected_path))

    if artifact_id:
        _mark_processed(artifact_id)


def run() -> None:
    registry = _load_registry(Path("agent_trading_company/orchestrator/registry.yml"))

    def on_ready(path: Path) -> None:
        if "/status/" in str(path):
            return
        handle_artifact(path, registry)

    handler = ArtifactReadyHandler(on_ready=on_ready)
    start_watcher([Path("artifacts"), Path("directives")], handler)

    # Emit startup artifact
    now = datetime.now(timezone.utc)
    startup_path = Path("artifacts/system/startup.md")
    content = (
        "---\n"
        f"artifact_id: \"startup-{now.strftime('%Y%m%d_%H%M%SZ')}\"\n"
        "agent_id: \"orchestrator-1\"\n"
        "role: \"orchestrator\"\n"
        f"created_at: \"{now.replace(microsecond=0).isoformat().replace('+00:00','Z')}\"\n"
        "inputs: []\n"
        "outputs: [\"artifacts/system/startup.md\"]\n"
        "directive_hash: \"" + compute_directive_hash(Path("directives/admin_directives.md").read_text(encoding="utf-8")) + "\"\n"
        "payload:\n"
        "  tick_type: \"startup\"\n"
        f"  tick_at: \"{now.replace(microsecond=0).isoformat().replace('+00:00','Z')}\"\n"
        "artifact_kind: \"system_startup\"\n"
        "status: \"completed\"\n"
        "---\n"
        "Startup tick.\n"
    )
    atomic_write(startup_path, content)


if __name__ == "__main__":
    run()
