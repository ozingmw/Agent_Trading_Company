from __future__ import annotations

from pathlib import Path

import pytest

from agent_trading_company.agents import executor
from agent_trading_company.kis import client as kis_client
from agent_trading_company.llm import router as llm_router


class DummyClient:
    def place_order(self, market_universe, exchange, symbol, side, qty, price, currency="USD"):
        return {"output": {"ODNO": "12345"}}


def test_executor_writes_execution_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        "  side: \"BUY\"\n"
        "  order_type: \"LIMIT\"\n"
        "  limit_price: 101\n"
        "  size_hint: 1\n"
        "  confidence: 0.6\n"
        "status: \"completed\"\n"
        "---\n",
        encoding="utf-8",
    )

    critic_path = tmp_path / "artifacts" / "critic" / "critic.md"
    critic_path.parent.mkdir(parents=True, exist_ok=True)
    critic_path.write_text(
        "---\n"
        "artifact_id: \"c1\"\n"
        "agent_id: \"critic-1\"\n"
        "role: \"critic\"\n"
        "created_at: \"2026-01-30T00:00:10Z\"\n"
        "inputs: []\n"
        "outputs: []\n"
        "directive_hash: \"hash\"\n"
        "payload:\n"
        "  recommendation: \"APPROVE\"\n"
        "  adjustment: null\n"
        "  notes: \"ok\"\n"
        "status: \"completed\"\n"
        "---\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(kis_client.KISClient, "from_env", lambda: DummyClient())

    class DummyRouter:
        def invoke(self, name, payload):
            return {
                "symbol": "AAPL",
                "exchange": "NASD",
                "side": "BUY",
                "order_type": "LIMIT",
                "limit_price": 101,
                "size_hint": 1,
                "critic_recommendation": "APPROVE",
            }

    llm_router.set_router(DummyRouter())

    output = executor.run(
        str(analyst_path),
        {"critic_artifact": str(critic_path), "market_universe": "OVERSEAS"},
        object(),
    )
    output_path = Path(output)
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "order_id" in content
    assert "critic_recommendation" in content
