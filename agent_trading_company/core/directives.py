from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Directives:
    market_universe: str = "KRX"
    trading_period: str = "09:00-15:30 KST"
    collection_interval_minutes: int = 5
    default_order_size: int = 1
    max_parallel_agents: int = 4
    symbol_universe_file: str = "config/universe.csv"
    data_budget_cap: int = 1000
    data_sources_enabled: list[str] = None  # type: ignore[assignment]
    leaderboard_cadence: str = "daily"

    def __post_init__(self) -> None:
        if self.data_sources_enabled is None:
            object.__setattr__(
                self, "data_sources_enabled", ["kis", "naver_finance"]
            )


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n")


def compute_directive_hash(content: str) -> str:
    normalized = _normalize_text(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _parse_front_matter(content: str) -> dict[str, Any]:
    lines = content.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines) or lines[idx].strip() != "---":
        return {}
    idx += 1
    fm_lines: list[str] = []
    while idx < len(lines) and lines[idx].strip() != "---":
        fm_lines.append(lines[idx])
        idx += 1
    if idx >= len(lines):
        return {}
    data = yaml.safe_load("\n".join(fm_lines))
    return data or {}


def load_directives(path: Path) -> tuple[Directives, str]:
    content = path.read_text(encoding="utf-8")
    data = _parse_front_matter(content)
    directives = Directives(
        market_universe=str(data.get("market_universe", "KRX")),
        trading_period=str(data.get("trading_period", "09:00-15:30 KST")),
        collection_interval_minutes=int(data.get("collection_interval_minutes", 5)),
        default_order_size=int(data.get("default_order_size", 1)),
        max_parallel_agents=int(data.get("max_parallel_agents", 4)),
        symbol_universe_file=str(data.get("symbol_universe_file", "config/universe.csv")),
        data_budget_cap=int(data.get("data_budget_cap", 1000)),
        data_sources_enabled=list(data.get("data_sources_enabled", ["kis", "naver_finance"])),
        leaderboard_cadence=str(data.get("leaderboard_cadence", "daily")),
    )
    return directives, compute_directive_hash(content)
