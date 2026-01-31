# Agent Trading Company MVP Plan

## TL;DR

**Before starting any work session, read `rules.md`.**

> **Quick Summary**: Build a live, autonomous, multi-agent trading system in Python using KIS OpenAPI, event-driven file handoffs, and markdown audit artifacts, with a Performance Judge that scores agents and drives prompt self-improvement.
>
> **Deliverables**:
> - Python package with agent framework, file contracts, and event-driven orchestration
> - KIS OpenAPI client with mocked integration tests
> - Initial agent roster (Collector, Analyst, Critic, Executor, Portfolio/Asset Manager, Performance Judge, Orchestrator)
> - Structured data store for raw data/state + markdown summaries
> - Admin directives file and status tracking
> - Automated test suite (pytest)
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Test/Contracts -> File Watcher + Store -> KIS Client -> Orchestrator -> Executor/Portfolio -> Judge/Prompt Updates

---

## Context

### Original Request
Build `agent_trading_company`, a live multi-agent stock trading firm where agents autonomously collect data, analyze, critique, execute trades, manage assets, and evaluate each other. Administrator sets global directives only. Results are recorded as markdown files. No backtesting/simulation.

### Interview Summary
**Key Discussions**:
- Live trading from day one using KIS OpenAPI; no paper trading or simulation.
- Agents run autonomously in parallel and coordinate via event-driven file handoffs; no polling loops.
- Admin broadcasts constraints via a shared markdown directives file.
- Raw data and state stored in a structured store with markdown summaries.
- Data sources: collect broadly; paid sources allowed with admin-configurable budget cap.
- No risk guardrails or kill switches (explicit requirement).
- Performance Judge agent scores others, chooses metrics (qualitative allowed), and determines payouts.
- Rewards are periodic leaderboard, admin-configurable cadence with default daily.
- Learning = prompt refinement based on Judge feedback; automatic self-updates.
- Python stack; test infrastructure should be created.

**Research Findings**:
- No test infrastructure exists in the repo.

### Metis Review
**Identified Gaps (addressed in plan)**:
- Explicit MVP agent roster defined.
- File contracts, atomic writes, and readiness signals defined.
- Structured store choice defaulted to SQLite for v1.
- Conflict resolution and signal aggregation defaulted.
- KIS rate limits and token handling included as configurable constraints.
- Crash recovery and agent heartbeat tracking included.

---

## Work Objectives

### Core Objective
Create a production-lean MVP for a live, autonomous trading firm built from cooperating/competing agents with event-driven coordination, audit-grade markdown records, and performance-driven prompt refinement.

### Concrete Deliverables
- `agent_trading_company/` Python package with core utilities and agents
- `directives/admin_directives.md` for global admin constraints
- Structured store (SQLite) for state and raw data metadata
- Markdown artifacts per agent run in `artifacts/`
- Automated test suite using pytest

### Definition of Done
- [ ] `pytest -q` passes for all new tests
- [ ] Agents write markdown artifacts with valid schema and references
- [ ] Orchestrator detects file events and dispatches agents
- [ ] KIS client tests pass with mocked responses (no live orders in tests)

### Must Have
- Event-driven file watcher (no polling loop)
- Atomic file writes and readiness signal
- Admin directives file and agent status tracking
- Performance Judge + prompt self-update

### Must NOT Have (Guardrails)
- No backtesting or simulation
- No UI/dashboard
- No risk limits or kill switches (explicit requirement)
- No message queue (filesystem only)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: YES (Tests-after)
- **Framework**: pytest

### Test Setup Task (required)
- Install pytest and create a minimal test that passes
- All subsequent tasks include pytest-based acceptance criteria

**Test isolation rule**:
- Tests use `tmp_path` for `state/`, `data/raw/`, `artifacts/`, and `prompts/`
- Runtime defaults to repo-relative paths

## Path Resolution

- Base directory defaults to current working directory for CLI runs
- Override via `ATC_BASE_DIR` env var
- All relative paths (`state/`, `data/raw/`, `artifacts/`, `directives/`, `prompts/`) are resolved under base dir
- Implement in `agent_trading_company/core/paths.py` with `get_base_dir()`

---

## Packaging & CLI

- Use `pyproject.toml` with setuptools as build backend
- Module entrypoints are executed via `python -m agent_trading_company.orchestrator.runner` and `python -m agent_trading_company.orchestrator.emit_tick`
- No console_scripts required for MVP
- `api/` and `utils/` are not packaged or used

---

## File Contracts (MVP)

**Artifact Root**: `artifacts/`

**Per-role directories**:
- `artifacts/collector/`
- `artifacts/analyst/`
- `artifacts/critic/`
- `artifacts/executor/`
- `artifacts/portfolio/`
- `artifacts/judge/`
- `artifacts/status/`
- `artifacts/leaderboard/`
- `artifacts/system/`

**Orchestrator artifacts**:
- Orchestrator writes to `artifacts/system/` (no `artifacts/orchestrator/` directory)

**Status files**:
- `artifacts/status/` files are NOT artifacts; they use the status schema only
- Watcher ignores `artifacts/status/` updates
- Status schema allows `idle` even though artifact `status` does not

**Filename pattern (recommended for standard artifacts)**:
`YYYYMMDD_HHMMSSZ_{agent_id}_{role}_{artifact_id}.md`

**Exceptions**:
- Artifacts in `artifacts/system/`, `artifacts/status/`, `artifacts/leaderboard/` may use custom names
- Routing relies on front matter (role + payload) instead of filename in those directories

**artifact_id generation**:
- Unique string required
- Recommended pattern: `{role}-{timestamp}-{uuid4}`

**Readiness signal**:
- Write to `*.md.tmp` then atomic rename to `*.md`
- Watcher only reacts to final `.md` creation

**Markdown front matter (required)**:
```
---
artifact_id: "<uuid>"
agent_id: "collector-1"
role: "collector"
created_at: "2026-01-29T12:00:00Z"
inputs: ["artifacts/collector/..."]
outputs: ["data/raw/...jsonl"]
directive_hash: "<sha256>"
references: ["https://apiportal.koreainvestment.com"]
status: "completed"
---
```

**Schema (authoritative)**:
- `artifact_id` (string, required)
- `agent_id` (string, required)
- `role` (enum: collector|analyst|critic|executor|portfolio|judge|orchestrator, required)
- `created_at` (ISO-8601 string, required)
- `inputs` (list of artifact paths, required; empty list allowed)
- `outputs` (list of data or artifact paths, required; empty list allowed)
- `directive_hash` (sha256 hex string, required)
- `references` (list of URLs or internal doc paths, optional)
- `artifact_kind` (string, optional; use for system/leaderboard/status)
- `payload` (map, required for non-system artifacts)
- `status` (enum: working|completed|error, required)

For roles without data outputs, include the artifact path in `outputs`.

**Time semantics**:
- `created_at` must be UTC ISO-8601 with `Z`
- Filename timestamps use UTC
- Conflict windows compare UTC times

**Payload schema by role (required in front matter as `payload`)**:
- collector.payload:
  - `sources` (list of strings)
  - `universe` (string)
  - `counts` (map: source -> int)
  - `outputs_by_source` (map: source -> path)
- analyst.payload:
  - `symbol` (string)
  - `exchange` (string)
  - `side` (BUY|SELL)
  - `order_type` (MARKET|LIMIT)
  - `limit_price` (number | null)
  - `size_hint` (number)
  - `confidence` (0-1)
- critic.payload:
  - `recommendation` (APPROVE|REJECT|ADJUST)
  - `adjustment` (map, optional)
  - `notes` (string)
- executor.payload:
  - `order_id` (string)
  - `status` (string)
  - `symbol` (string)
  - `critic_recommendation` (APPROVE|REJECT|ADJUST)
- portfolio.payload:
  - `cash` (number)
  - `positions_count` (int)
  - `pnl_total` (number)
- judge.payload:
  - `leaderboard_top` (string)
  - `scores` (map: agent_id -> number)
  - `rationale` (string, optional)
- orchestrator.payload:
  - `tick_type` (string)
  - `tick_at` (ISO-8601 string)

**Directive hash algorithm**:
- SHA256 of UTF-8 bytes of `directives/admin_directives.md`
- Normalize line endings to `\n`
- Do not trim whitespace or reorder lines

**Artifact Examples**:

Collector:
```
---
artifact_id: "c1-20260129-120000"
agent_id: "collector-1"
role: "collector"
created_at: "2026-01-29T12:00:00Z"
inputs: []
outputs: ["data/raw/20260129/kis_quotes.jsonl"]
directive_hash: "<sha256>"
payload:
  sources: ["kis", "naver_finance"]
  universe: "KRX"
  counts:
    kis: 120
    naver_finance: 10
  outputs_by_source:
    kis: "data/raw/20260129/kis_quotes.jsonl"
    naver_finance: "data/raw/20260129/naver_news.jsonl"
status: "completed"
---
Collected KIS quotes for universe=KRX. 120 symbols.
```

Analyst:
```
---
artifact_id: "a1-20260129-120100"
agent_id: "analyst-1"
role: "analyst"
created_at: "2026-01-29T12:01:00Z"
inputs: ["artifacts/collector/20260129_120000Z_collector-1_collector_c1.md"]
outputs: ["artifacts/analyst/20260129_120100Z_analyst-1_analyst_a1.md"]
directive_hash: "<sha256>"
payload:
  symbol: "005930.KS"
  exchange: "KRX"
  side: "BUY"
  order_type: "LIMIT"
  limit_price: 70000
  size_hint: 100
  confidence: 0.62
status: "completed"
---
Signal: BUY 005930.KS confidence=0.62
```

Critic:
```
---
artifact_id: "cr1-20260129-120130"
agent_id: "critic-1"
role: "critic"
created_at: "2026-01-29T12:01:30Z"
inputs: ["artifacts/analyst/20260129_120100Z_analyst-1_analyst_a1.md"]
outputs: ["artifacts/critic/20260129_120130Z_critic-1_critic_cr1.md"]
directive_hash: "<sha256>"
payload:
  recommendation: "APPROVE"
  adjustment: null
  notes: "No issues detected"
status: "completed"
---
Critic approves the signal.
```

Executor:
```
---
artifact_id: "e1-20260129-120200"
agent_id: "executor-1"
role: "executor"
created_at: "2026-01-29T12:02:00Z"
inputs: ["artifacts/analyst/20260129_120100Z_analyst-1_analyst_a1.md", "artifacts/critic/20260129_120130Z_critic-1_critic_cr1.md"]
outputs: ["artifacts/executor/20260129_120200Z_executor-1_executor_e1.md"]
directive_hash: "<sha256>"
payload:
  order_id: "12345"
  status: "SUBMITTED"
  symbol: "005930.KS"
  critic_recommendation: "APPROVE"
status: "completed"
---
Order submitted: order_id=12345 status=SUBMITTED symbol=005930.KS
```

Portfolio:
```
---
artifact_id: "p1-20260129-152900"
agent_id: "portfolio-1"
role: "portfolio"
created_at: "2026-01-29T15:29:00Z"
inputs: ["artifacts/executor/20260129_120200Z_executor-1_executor_e1.md"]
outputs: ["artifacts/portfolio/20260129_152900Z_portfolio-1_portfolio_p1.md"]
directive_hash: "<sha256>"
payload:
  cash: 1000000
  positions_count: 12
  pnl_total: 35000
status: "completed"
---
Portfolio snapshot updated.
```

Judge:
```
---
artifact_id: "j1-20260129-153000"
agent_id: "judge-1"
role: "judge"
created_at: "2026-01-29T15:30:00Z"
inputs: ["artifacts/portfolio/20260129_152900Z_portfolio-1_portfolio_p1.md"]
outputs: ["artifacts/leaderboard/20260129_153000Z_judge-1_leaderboard_j1.md"]
directive_hash: "<sha256>"
payload:
  leaderboard_top: "analyst-1"
  scores:
    analyst-1: 1.42
    analyst-2: 0.97
artifact_kind: "leaderboard"
status: "completed"
---
Leaderboard updated. Top agent: analyst-1 score=1.42
```

Startup (orchestrator):
```
---
artifact_id: "orch-20260129-115959-uuid"
agent_id: "orchestrator-1"
role: "orchestrator"
created_at: "2026-01-29T11:59:59Z"
inputs: []
outputs: ["artifacts/system/startup.md"]
directive_hash: "<sha256>"
payload:
  tick_type: "startup"
  tick_at: "2026-01-29T11:59:59Z"
artifact_kind: "system_startup"
status: "completed"
---
Orchestrator startup tick.
```

Tick (orchestrator):
```
---
artifact_id: "tick-20260129-120000-uuid"
agent_id: "orchestrator-1"
role: "orchestrator"
created_at: "2026-01-29T12:00:00Z"
inputs: []
outputs: ["artifacts/system/tick-20260129_120000Z.md"]
directive_hash: "<sha256>"
payload:
  tick_type: "interval"
  tick_at: "2026-01-29T12:00:00Z"
artifact_kind: "system_tick"
status: "completed"
---
Interval tick.
```

**Status files**:
- `artifacts/status/{agent_id}.md` with status: `working | idle | completed | error`

---

## Routing & Triggers

**Startup trigger**:
- Orchestrator writes `artifacts/system/startup.md` at launch (role=orchestrator)
- This event triggers the Collector once

**Routing table**:
- `role=orchestrator` and `payload.tick_type=interval` -> triggers `collector`
- `role=orchestrator` and `payload.tick_type=startup` -> triggers `collector`
- `collector` artifact -> triggers `analyst`
- `analyst` artifact -> triggers `critic`
- `critic` artifact -> triggers `executor`
- `executor` artifact -> triggers `portfolio`
- `portfolio` artifact -> triggers `judge`
- `judge` artifact -> updates leaderboard + prompt files

**Conflict resolution (bootstrap)**:
- Conflict = multiple analyst artifacts for same `(symbol, exchange)` within 10 minutes with different `side`
- Window uses `created_at` timestamps in UTC; compare against latest analyst artifact time
- Score = `(judge_score or 1.0) * confidence`
- `judge_score` is read from latest leaderboard artifact in `artifacts/leaderboard/`
- `judge_score` is read from `payload.scores[agent_id]` in latest leaderboard artifact
- Pick highest score; tie-breaker = latest `created_at`
- Orchestrator discovers candidates by scanning `artifacts/analyst/` within the time window

---

## Agent Roster & Fan-out Rules

**Default roster (MVP)**:
- 1 Collector, 1 Analyst, 1 Critic, 1 Executor, 1 Portfolio, 1 Judge, 1 Orchestrator

**Fan-out**:
- Collector writes one artifact per tick containing JSONL paths for many symbols
- Orchestrator dispatches Analyst once per symbol listed in latest collector JSONL
- Analyst writes one artifact per symbol
- Symbols are taken from `collector.payload.outputs_by_source.kis` JSONL only
- Analyst runs are serialized per `agent_id` (one at a time); status file reflects current symbol

**Event types**:
- React to `.md` create or move events (treat move-to-`.md` as ready)
- Ignore modify events for `.md.tmp`
- Ignore events under `artifacts/status/`

**No polling rule**:
- External scheduler writes `artifacts/system/tick-YYYYMMDD_HHMMSSZ.md` on interval from directives
- Tick triggers Collector -> Analyst -> Critic -> Executor -> Portfolio -> Judge
- Daily leaderboard uses the same tick mechanism with `leaderboard_cadence`

**External scheduler responsibility**:
- Run a cron-like job that writes a tick artifact (example command to implement later):
  - `python -m agent_trading_company.orchestrator.emit_tick --now`
- MVP supports manual ticks only; scheduled ticks are optional

---

## Admin Directives Schema

**File**: `directives/admin_directives.md`

**Format**:
```
---
market_universe: "KRX" | "OVERSEAS"
trading_period: "09:00-15:30 KST"
collection_interval_minutes: 5
default_order_size: 1
max_parallel_agents: 4
symbol_universe_file: "config/universe.csv"
data_budget_cap: 1000
data_sources_enabled: ["kis", "dart", "naver_finance", "naver_board"]
leaderboard_cadence: "daily"
---
```

**System defaults** (if missing and no previous value):
- market_universe: KRX
- trading_period: "09:00-15:30 KST"
- collection_interval_minutes: 5
- default_order_size: 1
- max_parallel_agents: 4
- symbol_universe_file: config/universe.csv
- data_budget_cap: 1000 (request-credits/day)
- data_sources_enabled: [kis, naver_finance]
- leaderboard_cadence: daily

**Parsing rules**:
- YAML front matter only; ignore markdown body text
- Missing fields default to previous value or system default
- `directive_hash` = SHA256 of normalized file contents (see File Contracts)
- Directive updates must be written as `admin_directives.md.tmp` then atomic rename to `admin_directives.md`

---

## Parsing & Validation Rules

**YAML parsing**:
- Use PyYAML `safe_load` for front matter parsing
- Skip leading blank lines, then the next line must be `---`
- Front matter ends at the next line that equals `---`
- Content outside the first `--- ... ---` block is ignored

**Directive hash bytes**:
- Read file in text mode with UTF-8
- Normalize `\r\n` to `\n`
- Hash the entire file content (front matter + body) exactly as stored
- Body text is included in hash intentionally for audit integrity
- Do not trim or add trailing newline before hashing

**Env loading**:
- Use `python-dotenv` to load `.env.local` then `.env` (if present)
- Fall back to `os.getenv` values when dotenv is disabled
- Load dotenv only in CLI entrypoints; if `DISABLE_DOTENV=1`, skip dotenv

---

## Market Scope Defaults & KIS Mapping (MVP)

**Default market_universe**:
- If missing, default to `KRX`

**Unsupported market behavior**:
- Only used for markets not supported by configured KIS endpoints

**KRX mode MVP behavior**:
- Collector runs `kis` + `dart` + `naver_board`
- Analyst/Executor/Portfolio run normally

**Analyst payload -> KIS params (OVERSEAS)**:
- `exchange` -> `OVRS_EXCG_CD` (NASD|NYSE|AMEX)
- `symbol` -> `PDNO` for orders; `SYMB` for price queries
- `order_type=MARKET` -> `OVRS_ORD_UNPR=0`, `ORD_DVSN="00"`
- `order_type=LIMIT` -> `OVRS_ORD_UNPR=limit_price`, `ORD_DVSN="00"` (per existing code)

**Exchange code mapping (MVP)**:
- `NASD` -> `EXCD=NASD`, `OVRS_EXCG_CD=NASD`
- `NYSE` -> `EXCD=NYSE`, `OVRS_EXCG_CD=NYSE`
- `AMEX` -> `EXCD=AMEX`, `OVRS_EXCG_CD=AMEX`

**KRX mapping (MVP)**:
- Use KIS domestic endpoints for price/orders (to implement)
- Analyst `exchange=KRX` maps to domestic market codes per KIS docs

---

## Symbol Universe Source

- Default universe file: `config/universe.csv`
- CSV columns: `symbol,exchange`
- Collector loads this file each tick and filters by `market_universe`
- Allowed exchanges (MVP): NASD, NYSE, AMEX
- Sample rows:
  - `AAPL,NASD`
  - `MSFT,NASD`

**KRX corp_code map**:
- `config/corp_code_map.csv` with columns: `symbol,corp_code`
- Required for DART ingestion when `market_universe=KRX`

---

## Collector Source Contracts (MVP)

**KIS quotes**:
- Endpoint: `/uapi/overseas-price/v1/quotations/price`
- Required fields: `EXCD`, `SYMB`
- JSONL schema: `{ts, source:"kis", symbol, exchange, price, raw}`

**Collector artifact rule**:
- One collector artifact per tick
- `payload.outputs_by_source` maps each source to its JSONL path

**DART disclosures**:
- Endpoint: `https://opendart.fss.or.kr/api/list.json`
- Required: `crtfc_key` from `DART_API_KEY`
- JSONL schema: `{ts, source:"dart", corp_code, report_nm, rcept_no, rcept_dt}`

**Naver Finance news**:
- Page: `https://finance.naver.com/news/`
- JSONL schema: `{ts, source:"naver_finance", title, url, published_at}`
 - Parsing: `requests` + `beautifulsoup4` (lxml parser)
 - Tests: mock HTTP with `responses` + HTML fixtures in `tests/fixtures/`

**Naver Finance board**:
- Page: `https://finance.naver.com/item/board.naver?code=<symbol>`
- JSONL schema: `{ts, source:"naver_board", symbol, title, url, posted_at}`
 - Parsing: `requests` + `beautifulsoup4` (lxml parser)
 - Tests: mock HTTP with `responses` + HTML fixtures in `tests/fixtures/`

**Failure behavior**:
- If a source is enabled but credentials missing, write an error artifact and skip that source

**Market applicability**:
- `market_universe=OVERSEAS`: use `kis` + `naver_finance`; skip `dart` and `naver_board`
- `market_universe=KRX`: enable `dart` + `naver_board` (requires corp_code mapping)

**Data budget enforcement**:
- Track per-source estimated cost and total usage in `state/data_budget.json`
- If usage exceeds `data_budget_cap`, disable new fetches and emit error artifact
- Units: request-credits per day; each HTTP call costs 1 credit; reset at UTC 00:00
- Schema: `{date, cap, used_total, used_by_source}`
- Increment counter before each HTTP request; skip request if `used_total + 1 > cap`

---

## MVP Agent Logic (Deterministic)

**Analyst**:
- Use last two KIS quote records for a symbol
- If price increased -> `side=BUY`, else `side=SELL`
- `size_hint` = `default_order_size` from directives

**Critic**:
 - Default `APPROVE` unless confidence < 0.3, then `REJECT`
 - Advisory only; does not block execution

**Executor**:
 - Convert analyst payload to KIS params per Market Mapping
 - Always execute selected analyst signal; include critic recommendation in executor artifact

**Portfolio**:
- `market_value` = sum(qty * last_price)
- `pnl_total` = (market_value + cash) - initial_cash
- `last_price` source: latest KIS quote from `data_registry`; if missing, fetch via KIS client
- `initial_cash` is set from first KIS balance response and stored in SQLite
- MVP assumes orders are filled at requested price (no partial fills)

**Judge**:
- Quant path: compute returns over last 20 ticks, score = mean / (stddev + 1e-9)
- Qual path: rubric score = avg(signal_quality, execution_success, directive_alignment)

---

## Storage Schema (SQLite)

**DB location**: `state/agent_state.sqlite`

**Tables**:
- `positions(position_id TEXT PK, agent_id TEXT, symbol TEXT, exchange TEXT, qty REAL, avg_price REAL, market_value REAL, updated_at TEXT)`
- `orders(order_id TEXT PK, agent_id TEXT, symbol TEXT, exchange TEXT, side TEXT, qty REAL, price REAL, order_type TEXT, status TEXT, created_at TEXT, updated_at TEXT, raw_response TEXT)`
- `pnl(pnl_id TEXT PK, agent_id TEXT, date TEXT, realized REAL, unrealized REAL, total REAL)`
- `data_registry(data_id TEXT PK, source TEXT, symbol TEXT, start_ts TEXT, end_ts TEXT, path TEXT, format TEXT, checksum TEXT, created_at TEXT)`

**Raw data format**:
- Default: JSONL files in `data/raw/`
- Optional: Parquet if `pyarrow` installed (explicitly optional)

---

## Store Interface (Required Methods)

`Store` is defined in `agent_trading_company/storage/store.py` as a Protocol/ABC with:
- `save_order(order)`
- `get_orders(filter)`
- `save_position(position)`
- `get_positions()`
- `save_pnl(pnl)`
- `get_pnl_window(n)`
- `register_data(source, path, metadata)`
- `get_latest_data(source)`

---

## Prompt Storage Contract

**Current prompt**:
- `prompts/{agent_id}.md`

**History**:
- `prompts/history/{agent_id}/{timestamp}_{hash}.md`

**Prompt format**:
```
---
agent_id: "analyst-1"
updated_at: "2026-01-29T15:30:00Z"
score: 1.42
directive_hash: "<sha256>"
---
<prompt text>
```

**Update rules**:
- Judge writes new prompt to `*.md.tmp` then atomic rename to `.md`
- History file is append-only; never overwritten
 - History filename hash = SHA256 of prompt text

**Initialization**:
- On first run, create `prompts/{agent_id}.md` from a minimal template with empty `## Judge Feedback`

---

## Judge Scoring & Prompt Update Rules

**Inputs**:
- Latest portfolio artifact (pnl fields)
- Latest analyst/critic/executor artifacts within current tick window

**Score output (minimum)**:
- `scores` (map: agent_id -> number)
- `leaderboard_top` (agent_id)
- `rationale` (string, optional)

**Active agents**:
- Defined by `agent_trading_company/orchestrator/registry.yml` entries with `enabled: true`

**Quantitative scoring**:
- Tick window = last 20 `artifact_kind=system_tick` artifacts in `artifacts/system/`
- Use matching portfolio artifacts for those ticks (by nearest `created_at`)
- Returns series = delta of `pnl_total` per tick; skip missing ticks
- Score = mean(returns) / (stddev(returns) + 1e-9)

**Qualitative scoring fallback**:
- Use rubric: signal quality, execution success, alignment with directives (1-5 each)

**Prompt update behavior**:
- Append a `## Judge Feedback` section to current prompt
- Keep prompt non-empty; reject empty updates
- Add prompt history entry and include its path in artifact `references`
 - If `## Judge Feedback` exists, append a new bullet `- {timestamp}: {summary}` under it

---

## Secrets Hygiene

- Tokens are fetched via `/oauth2/tokenP` and cached in `state/token_info.json`
- Ensure `.env` and token files are excluded by `.gitignore`
- Tests must never read `.env` or real tokens
- If `.env` exists, keep it local; load `.env.local` first in runtime
- Never commit or upload secrets (API keys, tokens, account numbers)

---

## Orchestrator Registry & Idempotency

**Registry file**: `agent_trading_company/orchestrator/registry.yml`

**Schema**:
```
- agent_id: "collector-1"
  role: "collector"
  handler: "agent_trading_company.agents.collector:run"
  enabled: true
```

**Idempotency**:
- Track processed `artifact_id` values in `state/processed_artifacts.json`
- If an artifact_id is already processed, skip re-processing
 - Schema: `{ "processed": { "artifact_id": "ISO-8601" } }`

**Status file schema** (`artifacts/status/{agent_id}.md`):
```
---
agent_id: "collector-1"
status: "working"
last_heartbeat: "2026-01-29T12:00:30Z"
current_task: "collect"
last_artifact: "artifacts/collector/20260129_120000Z_collector-1_collector_c1.md"
---
```

---

## Dispatch & Concurrency Model

- Orchestrator is a long-lived process started via:
  - `python -m agent_trading_company.orchestrator.runner`
- Orchestrator starts watcher before emitting `startup` artifact
- On startup, perform one-time scan of `artifacts/` (excluding `status/`) to enqueue unprocessed artifacts
- Event queue receives `artifact_path` and `event_type`
- Handler interface: `run(artifact_path: str, directives: dict, store: Store) -> str`
- Concurrency: ThreadPool with `max_parallel_agents` from directives
- Debounce: ignore duplicate events for same `artifact_id` within 2 seconds
- Heartbeat cadence: every 10 seconds while working
- Stale threshold: mark `status: error` if `now - last_heartbeat > 60s`

---

## Locking Rules

- Use file locks for:
  - `state/processed_artifacts.json`
  - `artifacts/status/{agent_id}.md`
  - `state/agent_state.sqlite` (single-writer transactions)
- Lock scope: lock file during write; release immediately after atomic rename
- fcntl locks are macOS/Linux only (MVP target)

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Foundations):
- Task 1: Test infrastructure + project skeleton
- Task 2: File contracts and markdown schema
- Task 3: Structured store layer

Wave 2 (Core Systems):
- Task 4: File watcher + atomic IO utilities
- Task 5: Admin directives + status tracking
- Task 6: KIS client wrapper

Wave 3 (Agents + Orchestration):
- Task 7: Orchestrator + conflict resolution
- Task 8: Data Collector agent
- Task 9: Analyst + Critic agents
- Task 10: Executor + Portfolio/Asset Manager
- Task 11: Performance Judge + prompt self-update

Critical Path: Task 1 -> Task 2 -> Task 4 -> Task 6 -> Task 7 -> Task 10 -> Task 11

---

## TODOs

> Implementation + Tests = ONE task. All acceptance criteria are automated.

- [x] 1. Initialize Python project + pytest infrastructure

  **What to do**:
  - Create Python package root `agent_trading_company/`
  - Add `pyproject.toml` (pytest, watchdog, requests, pydantic, responses, pyyaml, python-dotenv, beautifulsoup4, lxml)
  - Set Python version requirement (>=3.11) in `pyproject.toml`
  - Add minimal test in `tests/test_smoke.py`
  - Add `.gitignore` entries for `.env`, `state/`, `data/raw/`
  - Add `.env.example` with required env vars (KIS + DART)
  - Initialize token cache at `state/token_info.json`
  - Create `config/universe.csv` with at least 2 sample rows
  - Create `config/corp_code_map.csv` with at least 1 sample row
  - If `.env` exists, keep it local; runtime loads `.env.local` first then `.env`
  - Create `agent_trading_company/core/paths.py` for base dir resolution

  **Must NOT do**:
  - Do not add any backtesting/simulation code

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: foundation setup for all future tasks
  - **Skills**: `git-master`
    - `git-master`: maintain clean structure and conventions
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 2-11
  - **Blocked By**: None

  **References**:
  - `pyproject.toml` - dependency and test configuration
  - `tests/test_smoke.py` - minimal test pattern
  - pytest docs: https://docs.pytest.org/en/stable/

  **Acceptance Criteria**:
  - [x] `pytest -q` passes with 1 test
  - [x] `.env.example` lists `REAL_APP_KEY`, `REAL_SECRET_KEY`, `REAL_CANO`, `REAL_ACNT_PRDT_CD`, `DART_API_KEY`
  - [x] `config/universe.csv` exists with `symbol,exchange` header
  - [x] `config/corp_code_map.csv` exists with `symbol,corp_code` header

- [x] 2. Define file contracts and markdown artifact schema

  **What to do**:
  - Create `agent_trading_company/core/contracts.py` for artifact schemas
  - Define markdown front matter fields (agent, role, timestamp, inputs, outputs, payload, references)
  - Add validation utilities for required fields
  - Validate role-specific payload schema
  - Implement schemas as Pydantic BaseModel classes

  **Must NOT do**:
  - Do not add guardrails or risk limits

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: system-wide contracts used by all agents
  - **Skills**: `git-master`
    - `git-master`: maintain consistent structure
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1)
  - **Parallel Group**: Wave 1 (with Task 3)
  - **Blocks**: Tasks 4-11
  - **Blocked By**: Task 1

  **References**:
  - `agent_trading_company/core/contracts.py` - schema definitions to create
  - `artifacts/` - target location for md outputs
  - File Contracts section in this plan - required fields and naming
  - Parsing & Validation Rules section in this plan

  **Acceptance Criteria**:
  - [x] `pytest tests/test_contracts.py -q` passes
  - [x] Contract validation rejects missing required fields for a sample artifact
  - [x] Payload schema validation fails for missing `symbol` in analyst artifacts

- [x] 3. Implement structured store layer (SQLite + raw data registry)

  **What to do**:
  - Create `agent_trading_company/storage/sqlite_store.py`
  - Create `agent_trading_company/storage/store.py` interface
  - Define tables for positions, orders, pnl, data_registry
  - Add raw data registry with file references to Parquet/JSON
  - Enable WAL mode and create-on-startup migrations
  - Migration strategy: `PRAGMA user_version` with `CREATE TABLE IF NOT EXISTS`

  **Must NOT do**:
  - Do not introduce non-SQLite databases in v1

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: foundational state layer
  - **Skills**: `git-master`
    - `git-master`: consistent migrations and schema
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 8-11
  - **Blocked By**: Task 1

  **References**:
  - SQLite docs: https://www.sqlite.org/lang.html
  - `agent_trading_company/storage/sqlite_store.py` - to create
  - `agent_trading_company/storage/store.py` - store interface
  - Storage Schema section in this plan - table definitions

  **Acceptance Criteria**:
  - [x] `pytest tests/test_storage.py -q` passes
  - [x] Tables exist at the configured store path with columns per Storage Schema section

- [x] 4. Implement atomic file IO + readiness signals + file watcher

  **What to do**:
  - Create `agent_trading_company/io/atomic_writer.py` with write-then-rename
  - Create `agent_trading_company/io/file_lock.py` (fcntl-based)
  - Create `agent_trading_company/io/watcher.py` using watchdog `Observer` (no polling)
  - Accept watchdog internal polling fallback as long as app code does not poll
  - Define readiness signal: final rename to `.md` indicates complete
  - Watch directories: `artifacts/` and `directives/`
  - Provide a handler class that can be unit-tested with synthetic events

  **Must NOT do**:
  - Do not implement polling loops

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: concurrency-sensitive infrastructure
  - **Skills**: `git-master`
    - `git-master`: clean IO abstractions
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 2)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 7-11
  - **Blocked By**: Task 2

  **References**:
  - watchdog docs: https://python-watchdog.readthedocs.io/en/stable/
  - `agent_trading_company/io/atomic_writer.py` - to create
  - `agent_trading_company/io/watcher.py` - to create

  **Acceptance Criteria**:
  - [x] `pytest tests/test_atomic_io.py -q` passes
  - [x] Tests write `.md.tmp` then rename to `.md` and watcher emits a ready event for the final path
  - [x] Tests invoke handler directly with synthetic `on_moved` and `on_created` events

- [x] 5. Admin directives + status tracking

  **What to do**:
- Create `directives/admin_directives.md`
- Create `agent_trading_company/core/directives.py` to parse directives
- Create `agent_trading_company/core/status_registry.py` for agent status
- Include directive fields: market universe, trading period, data budget cap, data source enable/disable, leaderboard cadence

  **Must NOT do**:
  - Do not add a UI for directives

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: admin controls and auditability
  - **Skills**: `git-master`
    - `git-master`: consistent file conventions
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 2)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 7-11
  - **Blocked By**: Task 2

  **References**:
  - `directives/admin_directives.md` - admin config
  - `agent_trading_company/core/directives.py` - to create
  - `agent_trading_company/core/status_registry.py` - to create
  - Admin Directives Schema section in this plan

  **Acceptance Criteria**:
  - [x] `pytest tests/test_directives.py -q` passes
  - [x] Directive changes update `directive_hash` per Parsing & Validation Rules

- [x] 6. KIS OpenAPI client wrapper (mock-tested)

  **What to do**:
  - Create `agent_trading_company/kis/client.py` for auth, orders, queries
  - Implement KIS client directly in `agent_trading_company/kis/client.py`
  - Implement token cache handling in `agent_trading_company/kis/client.py` (state/token_info.json)
  - Route endpoint selection based on `market_universe` directive (KRX vs overseas)
  - Add rate-limit handling: retry on 429/5xx with exponential backoff (base 0.5s, max 3 retries, jitter +/-0.1s; inject sleep for tests)
  - Implement token caching using `state/token_info.json`
  - Document required env vars: `REAL_APP_KEY`, `REAL_SECRET_KEY`, `REAL_CANO`, `REAL_ACNT_PRDT_CD`
  - Preserve `ID_TYPE = REAL` behavior (no directive override in MVP)
  - Define `UnsupportedMarket` in `agent_trading_company/kis/errors.py`
  - MVP API surface (from existing code):
    - POST `/oauth2/tokenP` (access token)
    - POST `/oauth2/Approval` (approval key)
    - GET `/uapi/overseas-stock/v1/trading/inquire-balance` (tr_id `TTTS3012R`)
    - GET `/uapi/overseas-price/v1/quotations/price` (tr_id `HHDFS00000300`)
    - GET `/uapi/overseas-price/v1/quotations/price-detail` (tr_id `HHDFS76200200`)
    - POST `/uapi/overseas-stock/v1/trading/order` (tr_id `TTTT1002U` buy, `TTTT1006U` sell)
  - Add domestic (KRX) endpoints per KIS docs (to implement):
    - Price query (domestic)
    - Order placement (domestic)
    - Balance inquiry (domestic)
  - Approval key is not used in MVP order flow; fetch only if required by future endpoints

  **Must NOT do**:
  - Do not place real orders in tests
  - Do not commit token cache or credentials to git

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: external API integration
  - **Skills**: `git-master`
    - `git-master`: stable client structure
  - **Skills Evaluated but Omitted**:
    - `dev-browser`: no live browsing required

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 10-11
  - **Blocked By**: Task 1

  **References**:
  - KIS OpenAPI docs: https://apiportal.koreainvestment.com
  - `agent_trading_company/kis/client.py` - to create
  - `agent_trading_company/kis/errors.py` - to create

  **Acceptance Criteria**:
  - [x] `pytest tests/test_kis_client.py -q` passes (mocked responses)
  - [x] Client reads required env vars and fails fast if missing
  - [x] If `market_universe=KRX`, client uses domestic endpoints (per KIS docs)
  - [x] Token cache reads/writes only `state/token_info.json` in tests

- [x] 7. Orchestrator and conflict resolution

  **What to do**:
  - Create `agent_trading_company/orchestrator/runner.py`
  - Register agents, watch for artifacts, dispatch on events
  - Implement conflict resolution: weighted by judge scores, pick highest score signal
  - Add agent heartbeats and crash detection (status-only, no trading guardrails)
  - Add `agent_trading_company/orchestrator/registry.yml` with agent_id -> role -> handler mapping
  - Add `agent_trading_company/orchestrator/emit_tick.py` CLI to write tick artifacts

  **Must NOT do**:
  - Do not add a polling loop

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: core coordination logic
  - **Skills**: `git-master`
    - `git-master`: consistent routing structure
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 4 and 5)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 8-11
  - **Blocked By**: Tasks 4, 5

  **References**:
  - `agent_trading_company/orchestrator/runner.py` - to create
  - `agent_trading_company/core/status_registry.py` - status updates
  - `agent_trading_company/orchestrator/registry.yml` - agent registry
  - `agent_trading_company/orchestrator/emit_tick.py` - tick CLI
  - File Contracts section in this plan - watched directories and naming

  **Acceptance Criteria**:
  - [x] `pytest tests/test_orchestrator.py -q` passes
  - [x] Orchestrator routes `collector` artifacts to analyst handler in tests
  - [x] Heartbeat status file updates are observed via direct file read (not watcher)
  - [x] Conflict resolution uses `(judge_score or 1.0) * confidence`
  - [x] Re-processing same `artifact_id` is skipped (idempotent)
  - [x] `python -m agent_trading_company.orchestrator.emit_tick --now` writes a valid tick artifact
  - [x] Orchestrator reloads directives on directives file move event

- [x] 8. Data Collector agent (v1 sources)

  **What to do**:
  - Create `agent_trading_company/agents/collector.py`
  - Ingest v1 sources: KIS market data, DART disclosures, Naver Finance news, public community sentiment (Naver Finance board)
  - Store raw data as JSONL in `data/raw/` and register in SQLite
  - Write markdown summary artifact with `outputs` referencing JSONL paths
  - Use `DART_API_KEY` for DART access (if missing, emit error artifact and skip DART)
  - Respect `market_universe` directive when selecting symbols
  - Load symbols from `config/universe.csv`
  - For KRX, map `symbol` -> `corp_code` via `config/corp_code_map.csv`

  **Must NOT do**:
  - Do not expand to unlimited data sources in v1

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: data ingestion breadth
  - **Skills**: `git-master`
    - `git-master`: consistent data artifact formats
  - **Skills Evaluated but Omitted**:
    - `dev-browser`: no live browsing required

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 3 and 7)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 9-11
  - **Blocked By**: Tasks 3, 7

  **References**:
  - DART API: https://opendart.fss.or.kr
  - Naver Finance: https://finance.naver.com
  - KIS OpenAPI docs: https://apiportal.koreainvestment.com
  - `agent_trading_company/agents/collector.py` - to create
  - `agent_trading_company/storage/sqlite_store.py` - data registry
  - `config/universe.csv` - symbol universe
  - `config/corp_code_map.csv` - KRX corp_code mapping

  **Acceptance Criteria**:
  - [x] `pytest tests/test_collector.py -q` passes
  - [x] Collector writes markdown summary with JSONL file references
  - [x] JSONL records include required keys per Collector Source Contracts
  - [x] If DART enabled and `DART_API_KEY` missing, emits error artifact and skips DART
  - [x] If `data_budget_cap` exceeded, emits error artifact and stops new fetches
  - [x] `state/data_budget.json` contains `{date, cap, used_total, used_by_source}`

- [ ] 9. Analyst + Critic agents

  **What to do**:
  - Create `agent_trading_company/agents/analyst.py`
  - Create `agent_trading_company/agents/critic.py`
  - Analyst reads collector artifacts and writes signal markdown
  - Critic reads analyst signals and writes critique markdown (advisory only)

  **Must NOT do**:
  - Do not block trading with hard guardrails

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: core decision logic
  - **Skills**: `git-master`
    - `git-master`: consistent artifact contracts
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 8)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 10-11
  - **Blocked By**: Task 8

  **References**:
  - `agent_trading_company/core/contracts.py` - artifact schema
  - `agent_trading_company/agents/analyst.py` - to create
  - `agent_trading_company/agents/critic.py` - to create

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_analyst.py -q` passes
  - [ ] `pytest tests/test_critic.py -q` passes
  - [ ] Tests use a sample collector artifact and assert required front matter fields

- [ ] 10. Executor + Portfolio/Asset Manager

  **What to do**:
  - Create `agent_trading_company/agents/executor.py`
  - Create `agent_trading_company/agents/portfolio.py`
  - Executor reads analyst + critic artifacts, places orders via KIS client, writes execution artifact
  - Portfolio agent updates positions, cash, and PnL in SQLite, writes markdown status
  - Executor records critic recommendation but does not block on it
  - If KIS client raises `UnsupportedMarket`, write error artifact and skip order

  **Must NOT do**:
  - Do not add kill switches or risk limits

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: live trade execution and state updates
  - **Skills**: `git-master`
    - `git-master`: reliable order flow structure
  - **Skills Evaluated but Omitted**:
    - `dev-browser`: no browser work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 6 and 7)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 6, 7

  **References**:
  - `agent_trading_company/kis/client.py` - API client
  - `agent_trading_company/storage/sqlite_store.py` - state updates
  - `agent_trading_company/agents/executor.py` - to create
  - `agent_trading_company/agents/portfolio.py` - to create

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_executor.py -q` passes (mocked KIS)
  - [ ] `pytest tests/test_portfolio.py -q` passes
  - [ ] Executor writes execution artifact with order_id and status fields
  - [ ] Execution artifact includes critic recommendation field
  - [ ] Portfolio stores `initial_cash` from first balance response and computes `pnl_total`

- [ ] 11. Performance Judge + prompt self-update

  **What to do**:
  - Create `agent_trading_company/agents/judge.py`
  - Judge evaluates agent outputs, computes scores (quantitative or qualitative)
  - Write leaderboard markdown and update per-agent prompt files automatically
  - Create prompt history log for each agent
  - Use `prompts/{agent_id}.md` and `prompts/history/{agent_id}/...` per Prompt Storage Contract
  - Seed initial prompts for each agent from the template

  **Must NOT do**:
  - Do not require manual admin approval for prompt updates

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: evaluation logic and prompt evolution
  - **Skills**: `git-master`
    - `git-master`: consistent prompt versioning
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: no UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 9 and 10)
  - **Parallel Group**: Wave 3
  - **Blocks**: None (final)
  - **Blocked By**: Tasks 9, 10

  **References**:
  - `agent_trading_company/agents/judge.py` - to create
  - `agent_trading_company/core/contracts.py` - artifact schema
  - `artifacts/leaderboard/` - leaderboard output location
  - Prompt Storage Contract section in this plan

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_judge.py -q` passes
  - [ ] Leaderboard md created with `payload.scores` for all active agents
  - [ ] Prompt history is append-only and its path appears in `references`
  - [ ] Initial prompts exist for all agents
  - [ ] Tests cover both quantitative (tick window) and qualitative fallback paths

---

---

## Success Criteria

### Verification Commands
```bash
pytest -q
```

### Local Runbook (Smoke)
```bash
python -m agent_trading_company.orchestrator.runner
python -m agent_trading_company.orchestrator.emit_tick --now
```
Expected artifacts appear under:
- `artifacts/system/`
- `artifacts/collector/` -> `artifacts/analyst/` -> `artifacts/critic/` -> `artifacts/executor/` -> `artifacts/portfolio/` -> `artifacts/leaderboard/`
Note: run smoke without KIS env vars to verify fail-fast and avoid real orders.

### Final Checklist
- [ ] All required agents produce markdown artifacts
- [ ] Orchestrator dispatches on file events
- [ ] KIS client tests pass with mocks
- [ ] No UI, no backtesting, no guardrails implemented
