from __future__ import annotations

import asyncio
import uuid

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent


class CoordinatorAgent(BaseAgent):
    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.context.config.app.cycle_seconds)
            if not self.context.session_manager.any_open():
                self.update_status("idle", last_action="markets closed")
                continue

            cycle_id = str(uuid.uuid4())
            self.update_status("running", last_action=f"cycle {cycle_id}")
            await self.emit(
                "CycleStarted",
                {"status": "started"},
                cycle_id=cycle_id,
            )

            symbols_kr = list(self.context.config.universe.seed_symbols_kr)
            symbols_us = list(self.context.config.universe.seed_symbols_us)
            await self.emit(
                "DataRequest",
                {"symbols_kr": symbols_kr, "symbols_us": symbols_us},
                cycle_id=cycle_id,
            )

            try:
                data_event = await self.context.bus.wait_for(
                    "MarketDataReady", cycle_id, timeout=20
                )
            except asyncio.TimeoutError:
                await self.emit(
                    "CycleCompleted",
                    {"status": "data_timeout"},
                    cycle_id=cycle_id,
                )
                continue

            if hasattr(self.context.broker, "update_prices"):
                quotes = data_event.payload.get("summary", {}).get("quotes", {})
                self.context.broker.update_prices(quotes)

            try:
                await self.context.bus.wait_for("SignalGenerated", cycle_id, timeout=20)
            except asyncio.TimeoutError:
                await self.emit(
                    "CycleCompleted",
                    {"status": "signal_timeout"},
                    cycle_id=cycle_id,
                )
                continue

            try:
                order_event = await self.context.bus.wait_for(
                    "OrderRequest", cycle_id, timeout=20
                )
            except asyncio.TimeoutError:
                await self.emit(
                    "CycleCompleted",
                    {"status": "order_timeout"},
                    cycle_id=cycle_id,
                )
                continue

            order_count = len(order_event.payload.get("orders", []))
            try:
                await self.context.bus.wait_for("OrderUpdate", cycle_id, timeout=20)
                order_status = "submitted"
            except asyncio.TimeoutError:
                order_status = "no_update"

            await self.emit(
                "CycleCompleted",
                {
                    "status": "completed",
                    "orders": order_count,
                    "order_status": order_status,
                },
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"cycle {cycle_id} complete")
