from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_trading_company.io.atomic_writer import atomic_write


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%Y%m%d_%H%M%SZ")


def build_tick_content(timestamp: datetime, tick_type: str, directive_hash: str) -> str:
    iso_ts = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    artifact_id = f"tick-{_format_timestamp(timestamp)}-{uuid4()}"
    return (
        "---\n"
        f"artifact_id: \"{artifact_id}\"\n"
        "agent_id: \"orchestrator-1\"\n"
        "role: \"orchestrator\"\n"
        f"created_at: \"{iso_ts}\"\n"
        "inputs: []\n"
        f"outputs: [\"artifacts/system/tick-{_format_timestamp(timestamp)}.md\"]\n"
        f"directive_hash: \"{directive_hash}\"\n"
        "payload:\n"
        f"  tick_type: \"{tick_type}\"\n"
        f"  tick_at: \"{iso_ts}\"\n"
        "artifact_kind: \"system_tick\"\n"
        "status: \"completed\"\n"
        "---\n"
        f"Tick emitted: {tick_type}\n"
    )


def emit_tick(now: datetime | None = None, tick_type: str = "interval") -> Path:
    timestamp = now or _now_utc()
    path = Path("artifacts/system") / f"tick-{_format_timestamp(timestamp)}.md"
    directive_path = Path("directives/admin_directives.md")
    directive_hash = ""
    if directive_path.exists():
        directive_hash = directive_path.read_text(encoding="utf-8")
        directive_hash = directive_hash.replace("\r\n", "\n")
        directive_hash = __import__("hashlib").sha256(directive_hash.encode("utf-8")).hexdigest()
    content = build_tick_content(timestamp, tick_type, directive_hash)
    return atomic_write(path, content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true", help="Emit tick now")
    parser.add_argument("--type", default="interval", help="Tick type")
    args = parser.parse_args()

    if args.now:
        emit_tick(tick_type=args.type)


if __name__ == "__main__":
    main()
