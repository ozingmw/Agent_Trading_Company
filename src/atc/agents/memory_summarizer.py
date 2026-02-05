from __future__ import annotations

from collections import Counter

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent


class MemorySummarizerAgent(BaseAgent):
    def _summarize(self, agent: str, events: list) -> str:
        agent_events = [event for event in events if event.source == agent]
        if not agent_events:
            return "No actions recorded."
        counts = Counter(event.type for event in agent_events)
        parts = [f"{key}:{value}" for key, value in counts.items()]
        last_event = agent_events[-1]
        return f"Events: {', '.join(parts)} | Last: {last_event.type}"

    async def run(self) -> None:
        queue = await self.context.bus.subscribe("CycleCompleted")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id or ""
            self.update_status("running", last_action=f"summarize {cycle_id}")
            events = await self.context.event_recorder.get_cycle_events(cycle_id)
            agents = {event.source for event in events}
            for agent in agents:
                summary = self._summarize(agent, events)
                self.context.memory_manager.append_entry(
                    agent, "Recent Actions", f"Cycle {cycle_id}: {summary}"
                )
            self.update_status("idle", last_action=f"summarize {cycle_id} done")
