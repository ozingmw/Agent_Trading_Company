from __future__ import annotations

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent
from atc.types import OrderRequest


class ExecutionAgent(BaseAgent):
    async def run(self) -> None:
        queue = await self.context.bus.subscribe("OrderRequest")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id
            self.update_status("running", last_action=f"execution {cycle_id}")
            orders = [OrderRequest.model_validate(o) for o in event.payload.get("orders", [])]
            results = []
            for order in orders:
                result = self.context.broker.place_order(order)
                results.append(result.model_dump())
            await self.emit(
                "OrderUpdate",
                {"results": results},
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"execution {cycle_id} done")
