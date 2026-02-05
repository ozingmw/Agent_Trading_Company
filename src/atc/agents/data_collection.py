from __future__ import annotations

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent


class DataCollectionAgent(BaseAgent):
    async def run(self) -> None:
        queue = await self.context.bus.subscribe("DataRequest")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id
            symbols_kr = event.payload.get("symbols_kr", [])
            symbols_us = event.payload.get("symbols_us", [])
            self.update_status("running", last_action=f"collecting {cycle_id}")
            summary = self.context.data_collector.collect(symbols_kr, symbols_us)
            await self.emit(
                "MarketDataReady",
                {"summary": summary.model_dump()},
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"data ready {cycle_id}")
