# Agent Guidelines (Global)

## Core principles
- Do not persist raw market data or post-trade operational records.
- Persist only audit logs, agent memories, and guideline docs.
- Use the event bus for coordination and keep messages concise.
- Respect long-only constraints and broker limits.
- Self-reflect daily and update your own memory file.

## Guideline updates
- Any agent can propose changes in `docs/agents/proposals/`.
- ContentPolicyManagerAgent reviews and merges proposals.
- All agents reload guidelines after a `GuidelineUpdated` event.
- Proposal files should be JSON with fields: `target`, `title`, `content`, `proposer`.

## Data handling
- Process KIS, news, and social data in memory only.
- Summaries and derived features may be referenced in audit logs.
- Universe updates are driven by DataCollectionAgent via `UniverseUpdated` events.

## Safety
- If unclear or data is missing, emit `HOLD` and explain why.
