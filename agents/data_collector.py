"""
Data Collector Agent - gathers market data and produces LLM-summarized snapshots.
"""

import json
import logging
from typing import Any

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


def _format_price(price: Any) -> dict:
    """Convert a StockPrice model to a plain dict for LLM context."""
    return {
        "current_price": price.stck_prpr,
        "open": price.stck_oprc,
        "high": price.stck_hgpr,
        "low": price.stck_lwpr,
        "volume": price.acml_vol,
        "change_rate_pct": price.prdy_ctrt,
        "change_amount": price.prdy_vrss,
    }


def _format_daily(daily_list: list) -> list[dict]:
    """Convert a list of DailyPrice models to plain dicts."""
    return [
        {
            "date": d.stck_bsop_date,
            "open": d.stck_oprc,
            "high": d.stck_hgpr,
            "low": d.stck_lwpr,
            "close": d.stck_clpr,
            "volume": d.acml_vol,
            "change_rate_pct": d.prdy_ctrt,
        }
        for d in daily_list
    ]


class DataCollectorAgent(BaseAgent):
    """Collects real-time and daily market data, then asks the LLM to summarize."""

    SYSTEM_PROMPT = (
        "You are a stock market data collection specialist for the Korean stock market "
        "(KOSPI/KOSDAQ).\n\n"
        "Analyze the raw market data provided and create a comprehensive market snapshot summary.\n"
        "Highlight: stocks with significant price changes, unusual volume patterns, and any "
        "notable market movements.\n"
        "Be concise, factual, and actionable. Your summary will be read by analysis and trading agents."
    )

    def __init__(self, name: str, config: Any, kis_client: Any) -> None:
        super().__init__(name, config, kis_client)

    async def run_cycle(self) -> dict:
        """Collect market data for every stock on the watchlist and summarize via LLM."""

        # 1. Read risk-manager reports for any watchlist / constraint adjustments
        risk_reports = self.read_other_reports("risk_manager", 1)

        # 2. Gather current price + recent daily prices for each stock
        market_data: dict[str, dict] = {}
        for code in self.config.watchlist:
            try:
                price = await self.kis.get_price(code)
                daily = await self.kis.get_daily_prices(code, count=5)
                market_data[code] = {
                    "current": _format_price(price),
                    "daily": _format_daily(daily),
                }
            except Exception as e:
                logger.warning("Failed to get data for %s: %s", code, e)

        if not market_data:
            logger.warning("No market data collected this cycle")

        # 3. Build context for the LLM
        context = self._build_context(market_data, risk_reports)

        # 4. Ask LLM for a human-readable summary
        llm_summary = await self.llm.ask(self.SYSTEM_PROMPT, context)

        # 5. Return structured report data (consumed by BaseAgent.run -> ReportManager)
        formatted_data = json.dumps(market_data, indent=2, ensure_ascii=False)
        return {
            "summary": llm_summary,
            "data": formatted_data,
            "llm_decision": llm_summary,
            "actions": f"Collected market data for {len(market_data)}/{len(self.config.watchlist)} watchlist stocks",
            "recommendations": "See summary for market highlights",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(market_data: dict, risk_reports: list[str]) -> str:
        """Assemble the LLM user-prompt from raw data and risk context."""
        parts: list[str] = ["## Current Market Data\n"]

        for code, info in market_data.items():
            cur = info["current"]
            parts.append(
                f"### Stock {code}\n"
                f"- Current price: {cur['current_price']}  Change: {cur['change_rate_pct']}%\n"
                f"- Open: {cur['open']}  High: {cur['high']}  Low: {cur['low']}\n"
                f"- Volume: {cur['volume']}\n"
            )
            if info["daily"]:
                parts.append("Recent daily history:")
                for d in info["daily"]:
                    parts.append(
                        f"  {d['date']}: O={d['open']} H={d['high']} L={d['low']} "
                        f"C={d['close']} Vol={d['volume']} Chg={d['change_rate_pct']}%"
                    )
            parts.append("")

        if risk_reports:
            parts.append("## Risk Manager Notes\n")
            parts.extend(risk_reports)

        return "\n".join(parts)
