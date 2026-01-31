# Agent Trading Company MVP

Event-driven, file-based multi-agent trading system (MVP) with KIS OpenAPI integration, markdown audit artifacts, and automated performance scoring.

## What’s Implemented

- File contracts for all agent artifacts (collector → analyst → critic → executor → portfolio → judge)
- Atomic IO + watchdog-based file readiness
- SQLite store for state + raw data registry
- Admin directives (`directives/admin_directives.md`)
- KIS client wrapper with mock-tested endpoints
- Orchestrator with routing, conflict resolution, idempotency, and tick emission
- Collector, Analyst, Critic, Executor, Portfolio, Judge agents
- Prompt auto-update + history tracking
- Full pytest suite

## Quick Start

### 1) Create venv and install deps
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

If you’re not using a requirements file, install the project dependencies manually:
```bash
.venv/bin/python -m pip install pytest watchdog requests pydantic responses pyyaml python-dotenv beautifulsoup4 lxml openai
```

### 2) Configure env
Copy `.env.example` to `.env` and set:
```
REAL_APP_KEY=
REAL_SECRET_KEY=
REAL_CANO=
REAL_ACNT_PRDT_CD=
DART_API_KEY=
OPENAI_API_KEY=
```

### 3) Run tests
```bash
.venv/bin/pytest -q
```

### 4) Start orchestrator + emit tick
```bash
python -m agent_trading_company.orchestrator.runner
python -m agent_trading_company.orchestrator.emit_tick --now
```

Artifacts will be written under:
```
artifacts/system/
artifacts/collector/
artifacts/analyst/
artifacts/critic/
artifacts/executor/
artifacts/portfolio/
artifacts/leaderboard/
```

## Project Structure

```
agent_trading_company/
  agents/              # collector, analyst, critic, executor, portfolio, judge
  core/                # directives, contracts, status
  io/                  # atomic_writer, watcher, file_lock
  kis/                 # KIS client wrapper
  orchestrator/        # runner, emit_tick, registry
  storage/             # SQLite store
directives/
  admin_directives.md
config/
  universe.csv
  corp_code_map.csv
```

## Notes

- No backtesting/simulation.
- No UI or guardrails.
- All data flows via markdown artifacts + JSONL raw data.

## Runbook (Smoke)

```bash
python -m agent_trading_company.orchestrator.runner
python -m agent_trading_company.orchestrator.emit_tick --now
```

Check artifacts under `artifacts/` and status under `artifacts/status/`.
