from __future__ import annotations

import hashlib
from pathlib import Path

from agent_trading_company.core.directives import compute_directive_hash, load_directives


def test_directives_parse_and_hash(tmp_path: Path) -> None:
    content = """---
market_universe: "KRX"
trading_period: "09:00-15:30 KST"
collection_interval_minutes: 5
default_order_size: 1
max_parallel_agents: 4
symbol_universe_file: "config/universe.csv"
data_budget_cap: 1000
data_sources_enabled: ["kis", "naver_finance"]
leaderboard_cadence: "daily"
---
"""
    path = tmp_path / "directives.md"
    path.write_text(content, encoding="utf-8")

    directives, directive_hash = load_directives(path)

    assert directives.market_universe == "KRX"
    assert directives.collection_interval_minutes == 5
    assert directives.data_sources_enabled == ["kis", "naver_finance"]
    assert directive_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_directive_hash_changes_on_content_update(tmp_path: Path) -> None:
    content = """---
market_universe: "KRX"
---
"""
    path = tmp_path / "directives.md"
    path.write_text(content, encoding="utf-8")
    _, first_hash = load_directives(path)

    updated = content + "# note\n"
    path.write_text(updated, encoding="utf-8")
    _, second_hash = load_directives(path)

    assert first_hash != second_hash
