from __future__ import annotations

from pathlib import Path

from agent_trading_company.agents import critic


def test_critic_writes_recommendation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / "admin_directives.md").write_text("---\n---\n", encoding="utf-8")

    analyst_path = tmp_path / "artifacts" / "analyst" / "analyst.md"
    analyst_path.parent.mkdir(parents=True, exist_ok=True)
    analyst_path.write_text(
        "---\n"
        "artifact_id: \"a1\"\n"
        "agent_id: \"analyst-1\"\n"
        "role: \"analyst\"\n"
        "created_at: \"2026-01-30T00:00:00Z\"\n"
        "inputs: []\n"
        "outputs: []\n"
        "directive_hash: \"hash\"\n"
        "payload:\n"
        "  symbol: \"AAPL\"\n"
        "  exchange: \"NASD\"\n"
        "  confidence: 0.4\n"
        "status: \"completed\"\n"
        "---\n",
        encoding="utf-8",
    )

    output = critic.run(str(analyst_path), {}, object())
    output_path = Path(output)
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "role: critic" in content
