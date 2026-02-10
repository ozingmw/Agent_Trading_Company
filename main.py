"""
Main entry point for Agent Trading Company.
Orchestrates all agents and the FastAPI server.
"""

import asyncio
import logging
import signal
import sys
from typing import List

import uvicorn

from config import Config
from kis.client import KISClient
from kis.ws_client import KISWebSocket
from agents.data_collector import DataCollectorAgent
from agents.data_analyst import DataAnalystAgent
from agents.trade_executor import TradeExecutorAgent
from agents.risk_manager import RiskManagerAgent
from server.app import create_app
from server.routes import set_kis_ws



def setup_logging(log_level: str) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("trading.log")
        ]
    )


def print_banner(config: Config) -> None:
    """Print startup banner."""
    banner = f"""
{'='*60}
  Agent Trading Company
{'='*60}
  Trading Mode: {config.trading_mode.upper()}
  API Port: {config.api_port}
  Watchlist: {', '.join(config.watchlist)}

  Agent Intervals:
    - Data Collector: {config.data_collector_interval}s
    - Data Analyst: {config.data_analyst_interval}s
    - Trade Executor: {config.trade_executor_interval}s
    - Risk Manager: {config.risk_manager_interval}s
{'='*60}
"""
    print(banner)


async def run_agent_loop(agent, interval: int) -> None:
    """Run an agent's execution loop with the specified interval."""
    logger = logging.getLogger(f"main.{agent.name}")
    try:
        await agent.run(interval)
    except asyncio.CancelledError:
        logger.info(f"Agent {agent.name} stopped")
    except Exception as e:
        logger.error(f"Agent {agent.name} fatal error: {e}", exc_info=True)


async def run_server(app, config: Config) -> None:
    """Run the FastAPI server."""
    server_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.api_port,
        log_level=config.log_level.lower()
    )
    server = uvicorn.Server(server_config)

    # Run server until shutdown
    await server.serve()


async def main() -> None:
    """Main application entry point."""
    # Initialize config
    config = Config()
    config.validate()

    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger("main")

    # Print startup banner
    print_banner(config)

    kis_client = None
    tasks: List[asyncio.Task] = []
    loop = asyncio.get_running_loop()

    # Signal handlers - cancel tasks directly from event loop
    def handle_shutdown(sig_name: str):
        logger.info(f"Received {sig_name}, initiating shutdown...")
        for task in tasks:
            if not task.done():
                task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown, sig.name)

    try:
        # Create KIS client
        kis_client = KISClient(config)
        await kis_client.__aenter__()
        logger.info("KIS client initialized")

        # Create agents
        agents = [
            DataCollectorAgent("data_collector", config, kis_client),
            DataAnalystAgent("data_analyst", config, kis_client),
            TradeExecutorAgent("trade_executor", config, kis_client),
            RiskManagerAgent("risk_manager", config, kis_client)
        ]
        logger.info(f"Created {len(agents)} agents")

        # Create FastAPI app
        app, ws_manager = create_app(agents, kis_client, config)
        logger.info("FastAPI app created")

        # Inject WebSocket manager into agents
        for agent in agents:
            agent._ws_manager = ws_manager

        # Create KIS real-time price stream
        async def on_price_tick(price: dict) -> None:
            """Relay KIS price ticks to frontend via WebSocket."""
            await ws_manager.broadcast("price_update", price)

        kis_ws = KISWebSocket(config, on_price=on_price_tick)
        set_kis_ws(kis_ws)

        tasks.append(asyncio.create_task(
            kis_ws.run(config.watchlist),
            name="kis_websocket"
        ))
        logger.info("KIS real-time price stream started for %s", config.watchlist)

        # Create agent tasks
        tasks.append(asyncio.create_task(
            run_agent_loop(agents[0], config.data_collector_interval),
            name="data_collector"
        ))
        tasks.append(asyncio.create_task(
            run_agent_loop(agents[1], config.data_analyst_interval),
            name="data_analyst"
        ))
        tasks.append(asyncio.create_task(
            run_agent_loop(agents[2], config.trade_executor_interval),
            name="trade_executor"
        ))
        tasks.append(asyncio.create_task(
            run_agent_loop(agents[3], config.risk_manager_interval),
            name="risk_manager"
        ))

        # Create server task
        tasks.append(asyncio.create_task(
            run_server(app, config),
            name="server"
        ))

        logger.info("All tasks started, running...")

        # Wait for all tasks (they exit via cancellation on signal)
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

    finally:
        # Cleanup - cancel any remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Close KIS client
        if kis_client:
            await kis_client.__aexit__(None, None, None)
            logger.info("KIS client closed")

        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
