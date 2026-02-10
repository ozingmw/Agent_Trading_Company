"""
Data Analyst Agent - reads collector snapshots and generates LLM-driven trading signals.
"""

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class DataAnalystAgent(BaseAgent):
    """Analyses market data and produces autonomous trading signals via LLM."""

    SYSTEM_PROMPT = (
        "You are a stock market analyst for the Korean market. "
        "Analyze the provided market data and generate trading signals.\n\n"
        "For each potential signal, provide:\n"
        "- stock_code: the stock ticker\n"
        "- action: \"buy\", \"sell\", or \"hold\"\n"
        "- confidence: 0.0 to 1.0\n"
        "- reasoning: brief explanation\n\n"
        "Consider: price trends, volume patterns, daily changes, and any risk constraints "
        "from the risk manager.\n\n"
        "You have FULL AUTONOMY to make analysis decisions. "
        "There are no restrictions on your analysis approach - you decide the methodology, "
        "thresholds, and criteria.\n\n"
        "Respond with JSON:\n"
        '{"signals": [{"stock_code": "...", "action": "buy"|"sell"|"hold", '
        '"confidence": 0.0, "reasoning": "..."}], '
        '"market_outlook": "...", "reasoning": "..."}'
    )

    def __init__(self, name: str, config: Any, kis_client: Any) -> None:
        super().__init__(name, config, kis_client)

    async def run_cycle(self) -> dict:
        """Read collector reports, ask LLM for analysis, return structured signals."""

        # 1. Gather context from other agents
        collector_reports = self.read_other_reports("data_collector", 3)
        risk_reports = self.read_other_reports("risk_manager", 1)

        if not collector_reports:
            logger.warning("No collector reports available - analysis may be limited")

        # 2. Build analysis prompt
        context = _build_analysis_context(collector_reports, risk_reports)

        # 3. Get LLM analysis (JSON mode)
        analysis = await self.llm.ask_json(self.SYSTEM_PROMPT, context)

        signals = analysis.get("signals", [])
        market_outlook = analysis.get("market_outlook", "N/A")
        reasoning = analysis.get("reasoning", "")

        logger.info(
            "Generated %d signal(s). Outlook: %s",
            len(signals),
            market_outlook,
        )

        return {
            "summary": f"Generated {len(signals)} signal(s). Outlook: {market_outlook}",
            "data": json.dumps(analysis, indent=2, ensure_ascii=False),
            "llm_decision": reasoning,
            "actions": "Analyzed market data and generated trading signals",
            "recommendations": json.dumps(signals, indent=2, ensure_ascii=False),
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _build_analysis_context(
    collector_reports: list[str],
    risk_reports: list[str],
) -> str:
    """Combine collector data and risk constraints into a single prompt."""
    parts: list[str] = []

    parts.append("## Recent Market Data\n")
    if collector_reports:
        parts.append("\n---\n".join(collector_reports))
    else:
        parts.append("(No market data reports available yet.)")

    parts.append("\n\n## Risk Constraints\n")
    if risk_reports:
        parts.append("\n---\n".join(risk_reports))
    else:
        parts.append("(No risk constraints issued yet - use your own judgment.)")

    return "\n".join(parts)
