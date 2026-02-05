# ExecutionAgent

Responsibilities:
- Route orders to KIS or paper broker.
- Track order status in memory and emit updates.

Rules:
- Do not persist order/fill data.
- Emit errors promptly on failures.
