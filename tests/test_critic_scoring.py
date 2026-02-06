from pathlib import Path

from atc.agents.base import AgentContext, AgentRegistry
from atc.agents.critic import CriticAgent
from atc.audit import AuditLog
from atc.config import AppConfig, Secrets
from atc.events import EventBus, EventRecorder
from atc.guidelines import GuidelineManager
from atc.memory import MemoryManager
from atc.session_manager import SessionManager
from atc.types import SignalBatch, SignalIntent
from atc.universe import UniverseManager


def _make_context(tmp_path: Path) -> AgentContext:
    config = AppConfig.model_validate(
        {
            "app": {"cycle_seconds": 60, "session_check_seconds": 60, "log_level": "INFO"},
            "markets": {"enable_kr": True, "enable_us": True},
            "kis": {
                "mode": "paper",
                "base_url_paper": "https://example.com",
                "base_url_live": "https://example.com",
                "token_url_paper": "https://example.com/token",
                "token_url_live": "https://example.com/token",
                "paper": {
                    "app_key_env": "KIS_PAPER_APP_KEY",
                    "app_secret_env": "KIS_PAPER_APP_SECRET",
                    "account_env": "KIS_PAPER_ACCOUNT_NO",
                },
                "live": {
                    "app_key_env": "KIS_LIVE_APP_KEY",
                    "app_secret_env": "KIS_LIVE_APP_SECRET",
                    "account_env": "KIS_LIVE_ACCOUNT_NO",
                },
            },
            "data_sources": {
                "newsapi_enabled": False,
                "newsapi_api_key_env": "NEWSAPI_KEY",
                "newsapi_query": "",
                "newsapi_language": "en",
                "naver_rss": [],
                "daum_rss": [],
                "reddit_enabled": False,
                "reddit_subreddits": [],
                "reddit_user_agent": "atc",
            },
            "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.2},
            "universe": {"seed_symbols_kr": [], "seed_symbols_us": [], "max_symbols": 10},
            "dashboard": {"host": "0.0.0.0", "port": 8000},
        }
    )
    secrets = Secrets()
    recorder = EventRecorder()
    bus = EventBus(recorder=recorder)
    audit = AuditLog(tmp_path / "audit.sqlite3")
    guidelines = GuidelineManager(tmp_path / "agent_guidelines.md", tmp_path / "agents")
    memory = MemoryManager(tmp_path / "memory")
    session = SessionManager(config.markets)
    universe = UniverseManager([], [], 10)
    return AgentContext(
        config=config,
        secrets=secrets,
        bus=bus,
        audit=audit,
        guideline_manager=guidelines,
        memory_manager=memory,
        session_manager=session,
        event_recorder=recorder,
        data_collector=object(),
        broker=object(),
        universe_manager=universe,
    )


def test_critic_score_batch(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    registry = AgentRegistry()
    agent = CriticAgent("CriticAgent", context, registry)
    batch = SignalBatch(
        intents=[
            SignalIntent(
                symbol="AAPL",
                market="US",
                action="BUY",
                confidence=0.6,
                horizon="intraday",
                order_type="MARKET",
                size=10,
                rationale="momentum",
                data_used=["news"],
            )
        ]
    )
    score, notes = agent._score_batch(batch)
    assert 0.0 <= score <= 1.0
    assert "intents=1" in notes
