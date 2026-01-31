from __future__ import annotations

from pathlib import Path

import pytest
import responses

from agent_trading_company.agents import collector
from agent_trading_company.core.directives import load_directives
from agent_trading_company.storage.sqlite_store import SQLiteStore
from agent_trading_company.llm import router as llm_router


@responses.activate
def test_collector_creates_artifact_and_registers_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    directives = directives_dir / "admin_directives.md"
    directives.write_text(
        "---\nmarket_universe: OVERSEAS\n"
        "data_sources_enabled: [kis, naver_finance]\n"
        "symbol_universe_file: config/universe.csv\n"
        "data_budget_cap: 1000\n"
        "---\n",
        encoding="utf-8",
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "universe.csv").write_text("symbol,exchange\nAAPL,NASD\n", encoding="utf-8")

    monkeypatch.setenv("REAL_APP_KEY", "key")
    monkeypatch.setenv("REAL_SECRET_KEY", "secret")
    monkeypatch.setenv("REAL_CANO", "123")
    monkeypatch.setenv("REAL_ACNT_PRDT_CD", "01")

    responses.add(
        responses.POST,
        "https://openapi.koreainvestment.com:9443/oauth2/tokenP",
        json={"access_token": "token", "expires_in": 3600},
        status=200,
    )
    responses.add(
        responses.GET,
        "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price",
        json={"output": {"last": "123"}},
        status=200,
    )

    fixture = Path(__file__).parent / "fixtures" / "naver_news.html"
    responses.add(
        responses.GET,
        "https://finance.naver.com/news/",
        body=fixture.read_text(encoding="utf-8"),
        status=200,
        content_type="text/html",
    )

    directives_obj, _ = load_directives(directives)
    store = SQLiteStore(db_path=tmp_path / "state" / "agent_state.sqlite")

    class DummyRouter:
        def invoke(self, name, payload):
            return {"sources": ["kis", "naver_finance"], "errors": []}

    llm_router.set_router(DummyRouter())
    artifact_path = collector.run("", directives_obj.__dict__, store)

    artifact_file = Path(artifact_path)
    assert artifact_file.exists()
    content = artifact_file.read_text(encoding="utf-8")
    assert "role: collector" in content

    registry = store.get_latest_data("kis")
    assert registry is not None
    assert registry["path"].endswith("kis_quotes.jsonl")

    budget_path = tmp_path / "state" / "data_budget.json"
    assert budget_path.exists()


@responses.activate
def test_collector_emits_error_on_missing_dart_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    directives = directives_dir / "admin_directives.md"
    directives.write_text(
        "---\nmarket_universe: KRX\n"
        "data_sources_enabled: [dart]\n"
        "symbol_universe_file: config/universe.csv\n"
        "data_budget_cap: 1000\n"
        "---\n",
        encoding="utf-8",
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "universe.csv").write_text("symbol,exchange\n005930,KRX\n", encoding="utf-8")

    directives_obj, _ = load_directives(directives)
    store = SQLiteStore(db_path=tmp_path / "state" / "agent_state.sqlite")

    class DummyRouter:
        def invoke(self, name, payload):
            return {"sources": ["dart"], "errors": []}

    llm_router.set_router(DummyRouter())
    artifact_path = collector.run("", directives_obj.__dict__, store)

    assert Path(artifact_path).exists()
    error_files = list((tmp_path / "artifacts" / "collector").glob("error_*.md"))
    assert error_files
