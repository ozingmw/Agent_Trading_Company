from __future__ import annotations

from pathlib import Path

import pytest

from agent_trading_company.agents import portfolio
from agent_trading_company.kis import client as kis_client
from agent_trading_company.storage.sqlite_store import SQLiteStore


class DummyClient:
    def get_balance(self, market_universe, exchange, currency):
        return {"output2": {"dnca_tot_amt": 1000000}}


def test_portfolio_writes_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / "admin_directives.md").write_text("---\n---\n", encoding="utf-8")

    execution_path = tmp_path / "artifacts" / "executor" / "executor.md"
    execution_path.parent.mkdir(parents=True, exist_ok=True)
    execution_path.write_text(
        "---\n"
        "artifact_id: \"e1\"\n"
        "agent_id: \"executor-1\"\n"
        "role: \"executor\"\n"
        "created_at: \"2026-01-30T00:00:00Z\"\n"
        "inputs: []\n"
        "outputs: []\n"
        "directive_hash: \"hash\"\n"
        "payload:\n"
        "  symbol: \"AAPL\"\n"
        "  status: \"SUBMITTED\"\n"
        "  order_id: \"123\"\n"
        "  critic_recommendation: \"APPROVE\"\n"
        "status: \"completed\"\n"
        "---\n",
        encoding="utf-8",
    )

    store = SQLiteStore(db_path=tmp_path / "state" / "agent_state.sqlite")
    monkeypatch.setattr(kis_client.KISClient, "from_env", lambda: DummyClient())

    output = portfolio.run(str(execution_path), {}, store)
    output_path = Path(output)
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "role: portfolio" in content
