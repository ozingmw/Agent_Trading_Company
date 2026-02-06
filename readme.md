# Agent Trading Company

Local multi-agent trading system for KR/US stocks using KIS. Includes agent memory, guidelines, critique, and a minimal ops dashboard.

## Quick start

1. Copy env template:
   - `cp .env.example .env`
2. Edit `config.toml` and `.env`.
3. Install deps:
   - `python -m pip install -e .[dev]`
4. Run the app:
   - `python -m atc.main`
5. Start the dashboard:
   - `cd web && npm install && npm run dev`

## Notes
- No raw market data or post-trade operational records are persisted.
- Agent audit logs are stored in `state/audit.sqlite3`.
- KIS paper and live credentials are separate (`KIS_PAPER_*` vs `KIS_LIVE_*`).
- Default OpenAI model is `gpt-5-mini`; override per mode with `OPENAI_MODEL_PAPER` and `OPENAI_MODEL_LIVE` (or `OPENAI_MODEL` globally).
- Model list reference: https://platform.openai.com/docs/api-reference/models/list
- If KIS credentials are configured, the broker uses KIS in both paper and live modes; otherwise it falls back to the local paper broker.
