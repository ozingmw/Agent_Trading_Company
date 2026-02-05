from __future__ import annotations

import asyncio
from datetime import datetime

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent


class SelfReflectionAgent(BaseAgent):
    async def run(self) -> None:
        last_reflection_date = None
        while True:
            await asyncio.sleep(600)
            if self.context.session_manager.any_open():
                continue
            today = datetime.utcnow().date()
            if last_reflection_date == today:
                continue

            statuses = self.registry.get_statuses()
            for agent_name in statuses.keys():
                feedback = self.context.memory_manager.latest_entry(agent_name, "Feedback")
                feedback_text = feedback or "No recent feedback."
                self.context.memory_manager.append_entry(
                    agent_name,
                    "Lessons",
                    f"Daily reflection: {feedback_text}",
                )
                self.context.memory_manager.append_entry(
                    agent_name,
                    "Next Adjustments",
                    "Review guidelines and improve data completeness.",
                )

            last_reflection_date = today
            await self.emit(
                "SelfReflectionComplete",
                {"agents": list(statuses.keys())},
                cycle_id=None,
            )
            self.update_status("idle", last_action="daily reflection complete")
