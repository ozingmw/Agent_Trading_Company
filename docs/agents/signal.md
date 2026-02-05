# SignalAgent

Responsibilities:
- Generate trading intents using LLM reasoning.
- Provide dynamic horizon, size, order type, and rationale.

Rules:
- If data quality is low, emit HOLD.
- Always include rationale and data_used fields.
