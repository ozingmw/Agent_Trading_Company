---
name: orchestrator_route
description: Decide next agents to route based on artifact role and payload.
---

Inputs:
- role: string
- payload: object
- enabled_agents: list of {agent_id, role}

Rules:
- Route chain: orchestrator(startup|interval)->collector->analyst->critic->executor->portfolio->judge
- Return list of agent_ids for next step

Return JSON:
{
  "targets": [string]
}
