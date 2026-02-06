from __future__ import annotations

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent
from atc.types import MarketDataSummary


class DataCollectionAgent(BaseAgent):
    async def run(self) -> None:
        queue = await self.context.bus.subscribe("DataRequest")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id
            symbols_kr = event.payload.get("symbols_kr", [])
            symbols_us = event.payload.get("symbols_us", [])
            self.update_status("running", last_action=f"collecting {cycle_id}")
            try:
                summary = self.context.data_collector.collect(symbols_kr, symbols_us)
                kr_candidates, us_candidates = self.context.data_collector.extract_symbol_candidates(summary)
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("data collection failed")
                summary = MarketDataSummary(notes=[f"data collection failed: {exc}"])
                kr_candidates, us_candidates = [], []
                await self.emit(
                    "Error",
                    {"message": f"data collection failed: {exc}"},
                    cycle_id=cycle_id,
                )
            self.context.universe_manager.update_trends(summary.trends)
            self.context.universe_manager.add_symbols(kr_candidates, us_candidates)
            await self.emit(
                "UniverseUpdated",
                {"symbols_kr": kr_candidates, "symbols_us": us_candidates, "trends": summary.trends},
                cycle_id=cycle_id,
            )
            await self.emit(
                "MarketDataReady",
                {"summary": summary.model_dump()},
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"data ready {cycle_id}")
