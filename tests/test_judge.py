from __future__ import annotations

from pathlib import Path

from agent_trading_company.agents import judge
from agent_trading_company.llm import router as llm_router


def _write_portfolio(path: Path, pnl_total: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "artifact_id: \"p1\"\n"
        "agent_id: \"portfolio-1\"\n"
        "role: \"portfolio\"\n"
        "created_at: \"2026-01-30T00:00:00Z\"\n"
        "inputs: []\n"
        "outputs: []\n"
        "directive_hash: \"hash\"\n"
        "payload:\n"
        f"  pnl_total: {pnl_total}\n"
        "  cash: 100\n"
        "  positions_count: 1\n"
        "status: \"completed\"\n"
        "---\n",
        encoding="utf-8",
    )


def test_judge_quant_and_prompt_history(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / "admin_directives.md").write_text("---\n---\n", encoding="utf-8")

    registry = tmp_path / "agent_trading_company" / "orchestrator"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / "registry.yml").write_text(
        "- agent_id: \"analyst-1\"\n  role: \"analyst\"\n  handler: \"x\"\n  enabled: true\n",
        encoding="utf-8",
    )

    class DummyRouter:
        def invoke(self, name, payload):
            return {"scores": {"analyst-1": 1.0}, "leaderboard_top": "analyst-1", "rationale": None}

    llm_router.set_router(DummyRouter())

    portfolio_dir = tmp_path / "artifacts" / "portfolio"
    _write_portfolio(portfolio_dir / "p1.md", 100)
    _write_portfolio(portfolio_dir / "p2.md", 110)

    leaderboard = judge.run("artifacts/portfolio/p1.md", {}, object())
    leaderboard_path = Path(leaderboard)
    assert leaderboard_path.exists()
    content = leaderboard_path.read_text(encoding="utf-8")
    assert "leaderboard" in content

    history_dir = tmp_path / "prompts" / "history" / "analyst-1"
    assert history_dir.exists()
    assert list(history_dir.glob("*.md"))


def test_judge_qualitative_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / "admin_directives.md").write_text("---\n---\n", encoding="utf-8")

    registry = tmp_path / "agent_trading_company" / "orchestrator"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / "registry.yml").write_text(
        "- agent_id: \"analyst-1\"\n  role: \"analyst\"\n  handler: \"x\"\n  enabled: true\n",
        encoding="utf-8",
    )

    class DummyRouter:
        def invoke(self, name, payload):
            return {"scores": {"analyst-1": 3.0}, "leaderboard_top": "analyst-1", "rationale": None}

    llm_router.set_router(DummyRouter())

    leaderboard = judge.run("artifacts/portfolio/p1.md", {}, object())
    assert Path(leaderboard).exists()
