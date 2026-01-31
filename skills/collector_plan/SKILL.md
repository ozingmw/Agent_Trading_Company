---
name: collector_plan
description: Decide which sources to fetch based on market universe, budget, and credentials.
---

Inputs:
- market_universe: "KRX"|"OVERSEAS"
- enabled_sources: list of strings
- budget_remaining: number
- has_kis: boolean
- has_dart: boolean

Rules:
- If budget_remaining <= 0: return no sources and error
- For OVERSEAS: allow kis + naver_finance
- For KRX: allow kis + dart + naver_board
- If required creds missing, exclude that source

Return JSON:
{
  "sources": [string],
  "errors": [string]
}
