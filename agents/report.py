"""
Report management for agent outputs.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ReportManager:
    """Manages reading and writing agent reports."""

    def __init__(self, agent_name: str, reports_dir: str = "reports") -> None:
        """
        Initialize report manager.

        Args:
            agent_name: Name of the agent this manager belongs to
            reports_dir: Base directory for all reports (default: "reports")
        """
        self.agent_name = agent_name
        self.reports_dir = Path(reports_dir)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create report directories for all known agents."""
        known_agents = [
            "data_collector",
            "data_analyst",
            "trade_executor",
            "risk_manager",
        ]
        for agent in known_agents:
            (self.reports_dir / agent).mkdir(parents=True, exist_ok=True)

    def write_report(self, data: dict) -> str:
        """
        Write markdown report, return filepath.

        Args:
            data: Report data dictionary with keys: summary, data, llm_decision,
                  actions, recommendations

        Returns:
            str: Path to the written report file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.md"
        filepath = self.reports_dir / self.agent_name / filename

        # Ensure directory exists (in case new agent type)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        content = f"# {self.agent_name} Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"## Summary\n{data.get('summary', 'N/A')}\n\n"
        content += f"## Data\n{data.get('data', 'N/A')}\n\n"
        content += f"## LLM Decision\n{data.get('llm_decision', 'N/A')}\n\n"
        content += f"## Actions Taken\n{data.get('actions', 'N/A')}\n\n"
        content += f"## Recommendations\n{data.get('recommendations', 'N/A')}\n"

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def read_reports(self, agent_name: str, n: int = 3) -> list[str]:
        """
        Read last N reports from any agent.

        Args:
            agent_name: Name of the agent to read reports from
            n: Number of recent reports to read (default: 3)

        Returns:
            list[str]: List of report contents
        """
        agent_dir = self.reports_dir / agent_name
        if not agent_dir.exists():
            return []

        files = sorted(agent_dir.glob("*.md"), reverse=True)[:n]
        return [f.read_text(encoding="utf-8") for f in files]

    def list_reports(self, agent_name: str) -> list[str]:
        """
        List report filenames for an agent.

        Args:
            agent_name: Name of the agent to list reports for

        Returns:
            list[str]: Sorted list of report filenames (newest first)
        """
        agent_dir = self.reports_dir / agent_name
        if not agent_dir.exists():
            return []

        return sorted([f.name for f in agent_dir.glob("*.md")], reverse=True)
