"""
Base agent class for all trading agents.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Any

from agents.llm import LLMClient
from agents.report import ReportManager
from agents.market_schedule import is_any_market_active

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all trading agents."""

    def __init__(
        self,
        name: str,
        config: Any,
        kis_client: Optional[Any] = None,
    ) -> None:
        self.name = name
        self.config = config
        self.kis = kis_client
        self.llm = LLMClient(config)
        self.report_manager = ReportManager(name)
        self.status = "idle"  # idle | running | error
        self.last_run: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self._ws_manager: Optional[Any] = None  # set by main.py for broadcasting events

    @abstractmethod
    async def run_cycle(self) -> dict:
        """
        Execute one agent cycle.

        Returns:
            dict: Cycle result containing summary, data, decisions, actions, etc.
        """
        pass

    async def run(self, interval_seconds: int = 60) -> None:
        """
        Main loop - runs cycles at the specified interval.

        Args:
            interval_seconds: Time to wait between cycles (default: 60s)
        """
        logger.info(f"Agent {self.name} starting with {interval_seconds}s interval")
        while True:
            # Skip cycle if no market is active (outside pre-scan + trading hours)
            if not is_any_market_active():
                if self.status != "idle":
                    self.status = "idle"
                    logger.info(f"Agent {self.name} sleeping - markets closed")
                    if self._ws_manager:
                        await self._ws_manager.broadcast(
                            "agent_status_changed", self.get_status()
                        )
                await asyncio.sleep(interval_seconds)
                continue

            self.status = "running"
            if self._ws_manager:
                await self._ws_manager.broadcast(
                    "agent_status_changed", self.get_status()
                )
            try:
                result = await self.run_cycle()
                report_path = self.report_manager.write_report(result)
                self.last_run = datetime.now()
                self.status = "idle"
                logger.info(f"Agent {self.name} cycle complete: {report_path}")

                # Broadcast event if ws_manager available
                if self._ws_manager:
                    await self._ws_manager.broadcast(
                        "agent_status_changed", self.get_status()
                    )
                    await self._ws_manager.broadcast(
                        "new_report", {"agent": self.name, "path": report_path}
                    )
            except Exception as e:
                self.status = "error"
                self.last_error = str(e)
                logger.error(f"Agent {self.name} error: {e}", exc_info=True)
                if self._ws_manager:
                    await self._ws_manager.broadcast(
                        "agent_status_changed", self.get_status()
                    )

            await asyncio.sleep(interval_seconds)

    def read_other_reports(self, agent_name: str, n: int = 3) -> list[str]:
        """
        Read recent reports from another agent.

        Args:
            agent_name: Name of the agent to read reports from
            n: Number of recent reports to read (default: 3)

        Returns:
            list[str]: List of report contents
        """
        return self.report_manager.read_reports(agent_name, n)

    def get_status(self) -> dict:
        """
        Return current agent status for API.

        Returns:
            dict: Status information including name, status, last_run, last_error
        """
        return {
            "name": self.name,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_error": self.last_error,
        }
