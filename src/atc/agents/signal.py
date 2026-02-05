from __future__ import annotations

import json

from openai import OpenAI
from pydantic import ValidationError

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent
from atc.types import MarketDataSummary, SignalBatch, SignalIntent


class SignalAgent(BaseAgent):
    def __init__(self, name: str, context: AgentContext, registry: AgentRegistry) -> None:
        super().__init__(name, context, registry)
        self.client = (
            OpenAI(api_key=context.secrets.openai_api_key)
            if context.secrets.openai_api_key
            else None
        )

    def _build_prompt(self, summary: MarketDataSummary) -> str:
        news_titles = [item.title for item in summary.news[:8]]
        social_titles = [item.title for item in summary.social[:8]]
        lines = [
            "You are a trading signal agent.",
            "Return JSON only:",
            "{\"intents\":[{\"symbol\",\"market\",\"action\",\"confidence\",\"horizon\",\"order_type\",\"limit_price\",\"size\",\"rationale\",\"data_used\"}]}.",
            "Use action BUY/SELL/HOLD, order_type MARKET/LIMIT.",
            "If unsure, output HOLD with size 0.",
            f"Quotes: {json.dumps(summary.quotes, ensure_ascii=True)}",
            f"News: {json.dumps(news_titles, ensure_ascii=True)}",
            f"Social: {json.dumps(social_titles, ensure_ascii=True)}",
        ]
        return "\n".join(lines)

    def _fallback_intents(self, summary: MarketDataSummary) -> SignalBatch:
        intents = []
        for symbol in summary.quotes.keys():
            intents.append(
                SignalIntent(
                    symbol=symbol,
                    market="US" if symbol.isalpha() else "KR",
                    action="HOLD",
                    confidence=0.0,
                    horizon="intraday",
                    order_type="MARKET",
                    size=0,
                    rationale="LLM unavailable; hold.",
                    data_used=[],
                )
            )
        return SignalBatch(intents=intents)

    async def run(self) -> None:
        queue = await self.context.bus.subscribe("MarketDataReady")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id
            summary = MarketDataSummary.model_validate(event.payload.get("summary", {}))
            self.update_status("running", last_action=f"signal {cycle_id}")

            if not self.client:
                batch = self._fallback_intents(summary)
                await self.emit(
                    "SignalGenerated",
                    {"intents": batch.model_dump()["intents"], "quotes": summary.quotes},
                    cycle_id=cycle_id,
                )
                self.update_status("idle", last_action=f"signal {cycle_id} hold")
                continue

            prompt = self._build_prompt(summary)
            response_text = ""
            batch = None
            try:
                response = self.client.responses.create(
                    model=self.context.config.llm.model,
                    input=prompt,
                    temperature=self.context.config.llm.temperature,
                )
                response_text = response.output_text
                payload = json.loads(response_text)
                batch = SignalBatch.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, Exception):  # noqa: BLE001
                batch = self._fallback_intents(summary)

            self.context.audit.log_event(
                self.name,
                "SignalPrompt",
                {
                    "quotes_count": len(summary.quotes),
                    "news_count": len(summary.news),
                    "social_count": len(summary.social),
                    "summary_notes": summary.notes,
                },
                cycle_id=cycle_id,
                prompt=f"Signal prompt with {len(summary.quotes)} quotes, {len(summary.news)} news, {len(summary.social)} social items.",
                response=response_text,
            )
            await self.emit(
                "SignalGenerated",
                {"intents": batch.model_dump()["intents"], "quotes": summary.quotes},
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"signal {cycle_id} done")
