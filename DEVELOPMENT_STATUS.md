# Development status

## Phase 1 — Foundation

Status: implemented and phase 1 runtime validation passed.

### Implemented

- Next.js and TypeScript dashboard shell
- FastAPI application and versioned auth/health routing
- SQLAlchemy base and secure password/JWT foundations
- PostgreSQL and Redis Docker Compose services
- Alembic migration framework
- Initial users migration
- Environment template and live-trading default-off configuration
- Health and security unit tests
- Responsive dark institutional dashboard routes

### Files created

- `apps/api/app/`
- `apps/api/tests/`
- `apps/api/migrations/`
- `apps/web/app/`
- `apps/web/components/`
- `docker-compose.yml`
- `.env.example`
- `DEVELOPMENT_STATUS.md`

### Pending for later phases

- Database-backed authentication and role middleware
- Dashboard APIs and WebSocket streams
- Simulation and MT5 broker adapters
- Trading engine, strategy, risk and execution modules
- PostgreSQL migration set for all trading records
- Backtesting, Telegram and broker credentials

## Phase 2 — MT5 connectivity foundation

Status: implemented; simulation adapter and Windows boundary validation passed.

### Implemented

- Broker connector interface
- Deterministic simulation account, instruments, ticks and historical candles
- Explicit simulated execution with protected-stop requirement and idempotency
- Windows-only MT5 adapter boundary with mandatory package isolation
- API account status, account and market discovery endpoints

### Verification

- `pytest -q`: 9 tests passed
- `/api/v1/accounts/status`: returned connected simulation state
- `/api/v1/markets`: returned EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD and XAUUSD
- Docker Compose configuration: valid
- Frontend production build: passed
- The adapter will never expose or execute live MT5 orders

## Phase 3 — Market analysis

Status: implemented and validated.

### Implemented

- EMA 20/50/200, RSI 14, MACD, ATR 14, Bollinger Bands, ADX and stochastic calculations
- Market structure and support/resistance analysis
- Market regime and multi-timeframe consensus classification
- Trend-following and breakout/retest strategy interfaces
- Completed-candle-only analysis endpoint
- Strategy evaluation without any broker-order execution path

### Verification

- `pytest -q`: 14 tests passed
- Frontend production build: passed
- EURUSD H1 analysis endpoint: returned completed candles, indicators, trend, structure and regime
- Unknown simulation symbols: rejected with HTTP 404
- Live trading remains disabled

## Phase 4 — Signal generation

Status: implemented and validated.

### Implemented

- Unique in-memory simulated signal records
- BUY/SELL validator with protective stop-loss checks
- Minimum 1:2 reward/risk validation
- Four-hour signal expiration
- Rejected-signal explanations
- Completed-candle-only generation
- Signal generation and listing API routes
- Strategies remain unable to submit broker orders

### Verification

- `pytest -q`: 18 tests passed
- EURUSD H1 signal generation endpoint: returned a simulated validated signal
- Signal listing endpoint: reachable
- Frontend dashboard: HTTP 200
- Live trading remains disabled

## Phase 5 — Risk-based position sizing

Status: implemented and validated for the simulation broker.

- Risk page calculates lot size from account equity, entry, stop-loss distance, and a 1% risk cap
- Uses decimal arithmetic and instrument tick/volume specifications
- Rounds volume down to the broker step and returns zero rather than exceeding risk to meet minimum volume
- Explicitly rejects disconnected accounts and does not claim MT5 sizing support until the Windows worker supplies symbol specifications
- Calculator is estimates-only and never submits orders
- Verification: 33 backend tests pass; frontend production build and Docker Compose validation pass

## Phase 6 — Market scanner

Status: implemented and validated for simulation quotes and the MT5 worker feed.

- Market scanner displays bid, ask, spread, symbol and quote timestamp
- Simulation and MT5 read-only data are explicitly labeled
- Quotes refresh every five seconds through the same-origin API proxy
- Worker resolves broker-specific symbol names and includes precision metadata
- Verification: 33 backend tests pass; updated frontend production build and focused lint pass

## Phase 7 — Signal generation interface

Status: implemented and validated for simulation data.

- Signals page can generate strategy candidates by instrument and timeframe
- Displays entry, stop, three targets, reward/risk, quality and validation details
- Signal list refreshes periodically and labels its in-memory, simulation-only status
- API reports validated signals as expired after their four-hour validity window
- Verification: 33 backend tests pass; frontend production build and focused lint pass

## Frontend broker controls

Status: implemented and verified.

- Dashboard and top navigation now poll live backend connection status
- Settings and dashboard include broker connection controls
- Simulation demo can be connected and disconnected
- Trading engine can be started and stopped only through backend controls
- MT5 remains isolated to the Windows worker
- Live trading remains disabled
- API and frontend connection status verified

## iPad/Codespaces access

- Frontend browser API calls now use a same-origin Next.js proxy to the backend
- Verified account status and demo connect requests through the proxy return HTTP 200
- Open the dashboard from the Codespaces Ports tab on port 3000; port 8000 need not be opened separately

## MT5 demo/live connection and paper-trading handoff

Status: connection flow and Windows worker implemented; real broker login awaits Windows validation.

- Settings includes an MT5 Demo/Live account selector, account/login, password and server form
- Live account selection requires read-only acknowledgement and only accepts a matching real MT5 account
- API encrypts credentials in memory and exposes them once to a bearer-token-authenticated worker
- Worker verifies account login, server and selected account type, and reports account/quote data
- MT5 adapter explicitly rejects order submission, modification and closing; trading is paper-only
- Live account connections cannot start the engine; live trading remains hard-disabled
- Missing backend encryption key or worker token produces an explicit API configuration error
- Real connection requires `MT5_ENCRYPTION_KEY`, `MT5_WORKER_TOKEN`, a reachable HTTPS API and an installed/running Windows MT5 terminal/worker
- Verification: 33 tests passed; frontend production build passed; Compose configuration and worker/API syntax checks passed
- Codespace currently reports no broker connected; actual MT5 authentication was not run because this environment is Linux and has no MT5 terminal/worker

### Verification

- Frontend production build: passed (`17/17` routes generated)
- Backend tests: `3 passed`
- Health endpoint: returned `{"status":"ok","database":"configured","redis":"configured","live_trading":false}`
- Dashboard route: returned HTTP 200
- Alembic migration: initial users migration applied to the local SQLite development database
- Docker services: Compose configuration created; PostgreSQL/Redis containers were not started because Docker daemon startup was unavailable in the current host session

### Outstanding configuration

- Provision PostgreSQL 16 and Redis 7 with `docker compose up --build`
- Set strong `JWT_SECRET` and broker credentials in `.env`
- Complete database-backed authentication before public deployment

### Safety state

Live trading is disabled and cannot be enabled by this Phase 1 implementation.
