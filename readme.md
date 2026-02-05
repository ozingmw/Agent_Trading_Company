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
