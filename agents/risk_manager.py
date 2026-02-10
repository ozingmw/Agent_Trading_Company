"""
Risk Manager Agent - autonomous portfolio risk assessment and constraint setting.
"""

import json
import logging
from typing import Any

from agents.base import BaseAgent
from kis.models import AccountBalance

logger = logging.getLogger(__name__)


def format_positions_for_risk(balance: AccountBalance, available_cash: int) -> str:
    """Render portfolio state for risk-assessment context."""
    lines: list[str] = [
        f"Total Evaluation: {balance.total_evlu_amt} KRW",
        f"Total P&L: {balance.total_evlu_pfls_amt} KRW",
        f"Available Cash: {available_cash:,} KRW",
        "",
        "### Holdings",
    ]

    active_items = [item for item in balance.items if int(item.hldg_qty) > 0]
    if not active_items:
        lines.append("(No current positions)")
    else:
        for item in active_items:
            lines.append(
                f"- {item.pdno} ({item.prdt_name}): "
                f"qty={item.hldg_qty}, avg_cost={item.pchs_avg_pric}, "
                f"cur_price={item.prpr}, pnl={item.evlu_pfls_amt} ({item.evlu_pfls_rt}%)"
            )

    return "\n".join(lines)


def build_risk_context(
    balance: AccountBalance,
    available_cash: int,
    collector_reports: list[str],
    analyst_reports: list[str],
    executor_reports: list[str],
    own_reports: list[str],
) -> str:
    """Assemble full context for the risk-assessment LLM call."""
    parts: list[str] = []

    parts.append("## Portfolio State\n")
    parts.append(format_positions_for_risk(balance, available_cash))

    parts.append("\n\n## Market Data (from Data Collector)\n")
    if collector_reports:
        parts.append("\n---\n".join(collector_reports))
    else:
        parts.append("(No market data reports available yet.)")

    parts.append("\n\n## Analyst Signals\n")
    if analyst_reports:
        parts.append("\n---\n".join(analyst_reports))
    else:
        parts.append("(No analyst reports available yet.)")

    parts.append("\n\n## Recent Trades\n")
    if executor_reports:
        parts.append("\n---\n".join(executor_reports))
    else:
        parts.append("(No trades executed yet.)")

    parts.append("\n\n## Previous Risk Assessments\n")
    if own_reports:
        parts.append("\n---\n".join(own_reports))
    else:
        parts.append("(First risk assessment cycle.)")

    return "\n".join(parts)


class RiskManagerAgent(BaseAgent):
    """Fully autonomous risk manager - the LLM decides all risk parameters and constraints."""

    SYSTEM_PROMPT = (
        "You are an autonomous portfolio risk manager for a Korean stock trading system.\n\n"
        "Evaluate the current portfolio risk based on all available data:\n"
        "- Current positions and their P&L\n"
        "- Recent trades and their outcomes\n"
        "- Market conditions from collector/analyst reports\n"
        "- Historical patterns from your own previous reports\n\n"
        "You have COMPLETE AUTONOMY over all risk decisions:\n"
        "- You decide max position sizes, concentration limits\n"
        "- You decide stop-loss levels and profit targets\n"
        "- You decide which stocks to restrict or allow\n"
        "- You set the overall risk level\n"
        "- There are NO hardcoded risk parameters - all decisions are yours\n\n"
        "Your recommendations will be read by the trade executor and data analyst.\n\n"
        "Respond with JSON:\n"
        "{\n"
        '  "risk_level": "conservative"|"moderate"|"aggressive",\n'
        '  "max_position_pct": <number>,\n'
        '  "max_single_order_value": <number>,\n'
        '  "blocked_stocks": ["...", ...],\n'
        '  "warnings": ["...", ...],\n'
        '  "portfolio_assessment": "...",\n'
        '  "recommendations": "..."\n'
        "}"
    )

    def __init__(self, name: str, config: Any, kis_client: Any) -> None:
        super().__init__(name, config, kis_client)

    async def run_cycle(self) -> dict:
        """Read all agents' reports, assess portfolio risk via LLM, broadcast warnings."""

        # 1. Read reports from every agent
        collector_reports = self.read_other_reports("data_collector", 2)
        analyst_reports = self.read_other_reports("data_analyst", 2)
        executor_reports = self.read_other_reports("trade_executor", 3)
        own_reports = self.read_other_reports("risk_manager", 2)

        # 2. Fetch live portfolio state
        balance = await self.kis.get_balance()
        available_cash = await self.kis.get_available_cash()

        # 3. Build risk-assessment context
        context = build_risk_context(
            balance, available_cash,
            collector_reports, analyst_reports, executor_reports, own_reports,
        )

        # 4. LLM decides risk parameters
        assessment = await self.llm.ask_json(self.SYSTEM_PROMPT, context)

        risk_level = assessment.get("risk_level", "N/A")
        warnings = assessment.get("warnings", [])
        portfolio_assessment = assessment.get("portfolio_assessment", "")
        recommendations = assessment.get("recommendations", "")
        max_pos = assessment.get("max_position_pct", "N/A")
        blocked = assessment.get("blocked_stocks", [])

        logger.info(
            "Risk level: %s | Warnings: %d | Blocked: %s",
            risk_level, len(warnings), blocked,
        )

        # 5. Broadcast risk alerts via WebSocket if any warnings exist
        if warnings and self._ws_manager:
            await self._ws_manager.broadcast(
                "risk_alert",
                {"risk_level": risk_level, "warnings": warnings},
            )

        return {
            "summary": f"Risk Level: {risk_level}. Warnings: {len(warnings)}",
            "data": json.dumps(assessment, indent=2, ensure_ascii=False),
            "llm_decision": portfolio_assessment,
            "actions": (
                f"Set risk constraints: max_position={max_pos}%, "
                f"blocked={blocked}"
            ),
            "recommendations": recommendations,
        }
