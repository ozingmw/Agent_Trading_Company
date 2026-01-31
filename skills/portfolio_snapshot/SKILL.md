---
name: portfolio_snapshot
description: Compute portfolio snapshot values from positions and cash.
---

Inputs:
- cash: number
- positions: list of {qty, market_value}
- initial_cash: number

Rules:
- positions_count = len(positions)
- market_value = sum(position.market_value)
- pnl_total = (market_value + cash) - initial_cash

Return JSON:
{
  "cash": number,
  "positions_count": number,
  "pnl_total": number
}
