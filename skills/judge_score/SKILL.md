---
name: judge_score
description: Score analyst agents and pick leaderboard top.
---

Inputs:
- returns: list of numbers (pnl deltas per tick)
- agent_ids: list of active analyst agent ids

Rules:
- score = mean(returns) / (stddev(returns) + 1e-9) if returns length >= 2
- if returns length < 2, use score=3.0
- assign same score to all agents for MVP
- leaderboard_top is first agent_id in list

Return JSON:
{
  "scores": {"agent_id": number},
  "leaderboard_top": string,
  "rationale": string|null
}
