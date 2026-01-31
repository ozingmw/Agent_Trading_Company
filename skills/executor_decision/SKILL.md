---
name: executor_decision
description: Decide order placement details from analyst + critic inputs.
---

Inputs:
- analyst: {symbol, exchange, side, order_type, limit_price, size_hint}
- critic: {recommendation}

Rules:
- Always execute the analyst signal
- Include critic recommendation in output

Return JSON:
{
  "symbol": string,
  "exchange": string,
  "side": "BUY"|"SELL",
  "order_type": "MARKET"|"LIMIT",
  "limit_price": number|null,
  "size_hint": number,
  "critic_recommendation": "APPROVE"|"REJECT"|"ADJUST"
}
