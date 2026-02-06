from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from atc.agent_runner import AgentRunner
from atc.agents import AgentContext, AgentRegistry
from atc.api import AppState, create_app
from atc.audit import AuditLog
from atc.brokers.kis_client import KisClient
from atc.brokers.paper_broker import PaperBroker
from atc.config import load_config, load_secrets
from atc.data.collector import DataCollector
from atc.events import EventBus, EventRecorder
from atc.guidelines import GuidelineManager
from atc.logging_utils import configure_logging
from atc.memory import MemoryManager
from atc.session_manager import SessionManager
from atc.universe import UniverseManager


async def main_async() -> None:
    config = load_config("config.toml")
    secrets = load_secrets(config)
    configure_logging(config.app.log_level)

    event_recorder = EventRecorder()
    bus = EventBus(recorder=event_recorder)
    audit = AuditLog("state/audit.sqlite3")
    guideline_manager = GuidelineManager("docs/agent_guidelines.md", "docs/agents")
    memory_manager = MemoryManager("memory")
    session_manager = SessionManager(config.markets)

    kis_client = KisClient(config, secrets)
    broker = kis_client if kis_client.enabled else PaperBroker()
    data_collector = DataCollector(config, secrets, kis_client)
    universe_manager = UniverseManager(
        config.universe.seed_symbols_kr,
        config.universe.seed_symbols_us,
        config.universe.max_symbols,
    )

    registry = AgentRegistry()
    context = AgentContext(
        config=config,
        secrets=secrets,
        bus=bus,
        audit=audit,
        guideline_manager=guideline_manager,
        memory_manager=memory_manager,
        session_manager=session_manager,
        event_recorder=event_recorder,
        data_collector=data_collector,
        broker=broker,
        universe_manager=universe_manager,
    )

    runner = AgentRunner(context, registry)
    app_state = AppState(
        bus=bus,
        audit=audit,
        broker=broker,
        registry=registry,
        universe_manager=universe_manager,
    )
    app = create_app(app_state)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.dashboard.host,
            port=config.dashboard.port,
            log_level=config.app.log_level.lower(),
        )
    )

    await asyncio.gather(runner.run(), server.serve())


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
