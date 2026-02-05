from __future__ import annotations

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent
from atc.types import OrderRequest, SignalBatch, SignalIntent


class PortfolioAgent(BaseAgent):
    async def run(self) -> None:
        queue = await self.context.bus.subscribe("SignalGenerated")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id
            self.update_status("running", last_action=f"portfolio {cycle_id}")
            batch = SignalBatch.model_validate({"intents": event.payload.get("intents", [])})
            quotes = event.payload.get("quotes", {})
            account = self.context.broker.get_account()
            cash = account.cash
            positions = account.positions
            orders: list[OrderRequest] = []

            for intent in batch.intents:
                if intent.action == "HOLD" or intent.size <= 0:
                    continue
                if intent.action == "SELL":
                    held = positions.get(intent.symbol, 0)
                    if held <= 0:
                        continue
                    qty = min(intent.size, held)
                    orders.append(
                        OrderRequest(
                            symbol=intent.symbol,
                            market=intent.market,
                            side="SELL",
                            quantity=qty,
                            order_type=intent.order_type,
                            limit_price=intent.limit_price,
                            rationale=intent.rationale,
                        )
                    )
                    continue

                price = quotes.get(intent.symbol)
                qty = intent.size
                if price:
                    max_affordable = int(cash // price)
                    qty = min(qty, max_affordable)
                if qty <= 0:
                    continue
                orders.append(
                    OrderRequest(
                        symbol=intent.symbol,
                        market=intent.market,
                        side="BUY",
                        quantity=qty,
                        order_type=intent.order_type,
                        limit_price=intent.limit_price,
                        rationale=intent.rationale,
                    )
                )

            await self.emit(
                "OrderRequest",
                {"orders": [order.model_dump() for order in orders]},
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"portfolio {cycle_id} done")
