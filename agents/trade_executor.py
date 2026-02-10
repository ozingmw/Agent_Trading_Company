"""
Trade Executor Agent - executes buy/sell orders autonomously based on analyst signals.
"""

import json
import logging
from typing import Any

from agents.base import BaseAgent
from kis.models import AccountBalance

logger = logging.getLogger(__name__)


def format_positions(balance: AccountBalance) -> str:
    """Render account holdings as a human-readable string for the LLM."""
    if not balance.items:
        return "(No current positions)"

    lines: list[str] = []
    for item in balance.items:
        # Skip zero-quantity ghost rows the API sometimes returns
        if int(item.hldg_qty) == 0:
            continue
        lines.append(
            f"- {item.pdno} ({item.prdt_name}): "
            f"qty={item.hldg_qty}, avg_cost={item.pchs_avg_pric}, "
            f"cur_price={item.prpr}, pnl={item.evlu_pfls_amt} ({item.evlu_pfls_rt}%)"
        )

    if not lines:
        return "(No current positions)"

    lines.insert(0, f"Total evaluation: {balance.total_evlu_amt} KRW")
    lines.insert(1, f"Total P&L: {balance.total_evlu_pfls_amt} KRW")
    return "\n".join(lines)


class TradeExecutorAgent(BaseAgent):
    """Fully autonomous trade executor - the LLM decides every aspect of order execution."""

    SYSTEM_PROMPT = (
        "You are an autonomous trade executor for the Korean stock market via KIS API.\n\n"
        "Given the analysis signals, current portfolio positions, available cash, and risk "
        "constraints:\n"
        "- Decide which trades to execute (buy/sell)\n"
        "- Determine quantities and order types\n"
        "- You have COMPLETE AUTONOMY over all trading decisions\n"
        "- You decide position sizes, loss limits, profit targets - everything\n"
        "- There are NO hardcoded restrictions - all decisions are yours\n\n"
        "Consider portfolio balance, diversification, and the risk manager's recommendations.\n\n"
        "Respond with JSON:\n"
        "{\n"
        '  "orders": [\n'
        '    {"stock_code": "...", "action": "buy"|"sell", "qty": N, '
        '"price": 0, "order_type": "01", "reasoning": "..."}\n'
        "  ],\n"
        '  "reasoning": "overall execution reasoning"\n'
        "}\n\n"
        'Set price=0 and order_type="01" for market orders. '
        'Use order_type="00" with a specific price for limit orders.\n'
        "If no trades should be made, return an empty orders list with reasoning."
    )

    def __init__(self, name: str, config: Any, kis_client: Any) -> None:
        super().__init__(name, config, kis_client)

    async def run_cycle(self) -> dict:
        """Read signals, portfolio state, and risk guidance; let LLM decide trades; execute."""

        # 1. Gather context from other agents
        analyst_reports = self.read_other_reports("data_analyst", 2)
        risk_reports = self.read_other_reports("risk_manager", 1)
        own_reports = self.read_other_reports("trade_executor", 2)

        # 2. Fetch live portfolio state
        balance = await self.kis.get_balance()
        available_cash = await self.kis.get_available_cash()

        # 3. Build execution context
        positions_str = format_positions(balance)
        context = _build_execution_context(
            analyst_reports, risk_reports, own_reports, positions_str, available_cash,
        )

        # 4. LLM decides what to trade
        decision = await self.llm.ask_json(self.SYSTEM_PROMPT, context)

        orders = decision.get("orders", [])
        reasoning = decision.get("reasoning", "")

        # 5. Execute each order
        executed: list[dict] = []
        for order in orders:
            result = await self._execute_single_order(order)
            executed.append(result)

        logger.info(
            "Executed %d/%d orders. Reasoning: %s",
            sum(1 for e in executed if e["result"] == "success"),
            len(orders),
            reasoning[:120],
        )

        return {
            "summary": f"Executed {len(executed)} order(s)",
            "data": json.dumps(executed, indent=2, ensure_ascii=False),
            "llm_decision": reasoning,
            "actions": json.dumps(
                [e["order"] for e in executed], indent=2, ensure_ascii=False
            ),
            "recommendations": "See actions for trade details",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_single_order(self, order: dict) -> dict:
        """Place one order via KIS and return a result dict."""
        stock_code = order.get("stock_code", "")
        action = order.get("action", "").lower()
        qty = int(order.get("qty", 0))
        price = int(order.get("price", 0))
        order_type = order.get("order_type", "01")

        try:
            if action == "buy":
                resp = await self.kis.buy(stock_code, qty, price, order_type)
            elif action == "sell":
                resp = await self.kis.sell(stock_code, qty, price, order_type)
            else:
                return {"order": order, "result": "skipped", "error": f"Unknown action: {action}"}

            # Broadcast trade event via WebSocket if available
            if self._ws_manager:
                await self._ws_manager.broadcast(
                    "trade_executed",
                    {"order": order, "status": "filled", "response_code": resp.rt_cd},
                )

            return {"order": order, "result": "success", "response": str(resp)}

        except Exception as e:
            logger.error("Order failed for %s %s x%d: %s", action, stock_code, qty, e)
            return {"order": order, "result": "failed", "error": str(e)}


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _build_execution_context(
    analyst_reports: list[str],
    risk_reports: list[str],
    own_reports: list[str],
    positions_str: str,
    available_cash: int,
) -> str:
    """Assemble the full context string for the trade-decision LLM call."""
    parts: list[str] = []

    parts.append("## Analysis Signals\n")
    if analyst_reports:
        parts.append("\n---\n".join(analyst_reports))
    else:
        parts.append("(No analyst reports available yet.)")

    parts.append(f"\n\n## Current Positions\n{positions_str}")
    parts.append(f"\nAvailable Cash: {available_cash:,} KRW")

    parts.append("\n\n## Risk Constraints\n")
    if risk_reports:
        parts.append("\n---\n".join(risk_reports))
    else:
        parts.append("(No risk constraints issued yet - use your own judgment.)")

    parts.append("\n\n## Recent Trade History\n")
    if own_reports:
        parts.append("\n---\n".join(own_reports))
    else:
        parts.append("(No previous trades.)")

    return "\n".join(parts)
