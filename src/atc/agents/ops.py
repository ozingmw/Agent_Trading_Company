from __future__ import annotations

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent


class OpsAgent(BaseAgent):
    async def run(self) -> None:
        queue = await self.context.bus.subscribe("*")
        while True:
            event = await queue.get()
            self.update_status("running", last_action=f"saw {event.type}")
            if event.type == "Error":
                await self.emit(
                    "OpsAlert",
                    {"message": event.payload.get("message", "unknown error")},
                    cycle_id=event.cycle_id,
                )
            self.update_status("idle", last_action=f"last {event.type}")
