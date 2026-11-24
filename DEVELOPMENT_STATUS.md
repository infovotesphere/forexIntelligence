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

Status: implemented for simulation and worker-fed MT5 candle data.

- Signals page supports scanning one selected timeframe or all M5, M15, M30, H1, H4 and D1 intervals
- Displays entry, stop, three targets, reward/risk, quality and validation details
- Scans return only validated setups, report rejected candidates, and format displayed reward/risk to two decimals; an empty scan is a successful result, not a service error
- Signal list refreshes periodically and identifies each signal's data source
- Uses broker candles and MT5 tick-size metadata when MT5 is selected; never substitutes simulated candles for a missing MT5 feed
- MT5 scans skip timeframes with unavailable candle history and report those gaps without simulation fallback
- API reports validated signals as expired after their four-hour validity window
- Verification: 33 backend tests pass; frontend production build and focused lint pass

## Phase 8 — Live dashboard overview

Status: implemented and validated.

- Dashboard shows connection type, account balance/equity, engine state, market quotes and recent signals
- Refreshes account, market and signal data every ten seconds
- Live MT5 is labeled read-only; simulation and live broker-data flags are no longer conflated in connection status
- Verification: frontend production build and focused lint pass; API suite updated for MT5 status labeling

## Phase 9 — Read-only position monitoring

Status: MT5 remains read-only; simulation positions support practice trading.

- Windows MT5 worker includes open broker positions in its authenticated heartbeat
- API validates and serves position snapshots, including side, volume, prices, floating P/L and protective levels
- Positions page refreshes periodically and labels broker data as read-only
- An independent virtual practice account can be used from Positions and Orders without switching or connecting a broker account
- Practice positions and deals are separate from broker positions/history; MT5 remains read-only
- Positions overlays open entry/current/stop/target levels on the full-width chart, supports radial timeframe selection, and provides tap/long-press practice-position actions with modify and bulk close
- The quick practice trade panel is compact; broker positions remain read-only while virtual practice positions can be modified or closed
- MT5 positions remain read-only; practice stop loss and take profit are optional and no practice order reaches a broker
- Simulation balances, open positions and closed practice deals are persisted in runtime state
- Verification: focused broker and simulation-adapter tests pass

## Phase 10 — Technical market analytics

Status: implemented for simulation candles and worker-fed MT5 candle history.

- Analytics page displays trend, market structure, regime, indicators, support/resistance and strategy candidates
- Instrument and timeframe can be selected on the page
- Uses MT5 worker candles when an MT5 account is selected and simulation candles otherwise
- Analysis refuses to fall back to simulation when the selected MT5 feed is stale or lacks the requested candle history
- UI labels the data source and reports missing MT5 timeframes
- Performance analytics remain unavailable until broker deals are reconciled into trades and daily aggregates
- Verification: analysis API tests pass; frontend production build and focused lint pass

## Phase 11 — MT5 deal history

Status: read-only worker handoff and dashboard view implemented.

- Windows MT5 worker reports up to 500 deals from the last 30 days
- API validates deal snapshots and computes net profit using Decimal profit, commission and swap fields
- PostgreSQL persists deal tickets idempotently per account, server and environment; repeated worker heartbeats do not duplicate records
- History page shows deal/order IDs, side, volume, price and P/L breakdown
- Raw MT5 deals are explicitly distinguished from strategy-attributed or reconciled application trades
- Simulation history includes closed practice executions and clearly distinguishes them from MT5 deals
- Verification: 36 backend tests pass; frontend production build and focused lint pass

## Signal price precision

- Candidate entry, stop and target levels are rounded to the symbol tick size before validation and display
- Reward/risk validation runs on the rounded prices, preventing floating-point artifacts from leaking into generated signals
- Regression coverage includes XAUUSD cent-tick prices

## Phase 12 — Strategy backtesting

Status: interactive candle replay supports M1 through D1 for simulation, Yahoo Finance and connected MT5 history.

- Backtest API replays selected strategies over completed candles and returns OHLCV data plus trade outcomes and R-based metrics
- Connected MT5 accounts use read-only broker candles and broker tick-size metadata; missing or stale history returns an error instead of falling back to generated data
- Interactive candlestick chart supports play/pause, stepping, speed selection, a replay position slider, zoom and pan; future metrics remain hidden until playback completes
- Chart replay can be expanded into a responsive fullscreen view and exited with Escape
- Backtesting is for historical analysis; new practice trades are opened from Positions or Orders, and MT5 remains read-only
- The touch-friendly practice ticket opens in a dialog and supports market, buy-stop and sell-stop orders, optional stop loss/take profit, and pending-order cancellation
- Yahoo Finance M1 history is limited to the latest seven days; MT5 M1 history depends on Windows-worker candle availability
- Completed replays show average R per trade and a realized-equity curve with cumulative R and drawdown after each closed trade
- The Windows worker sends up to 2,001 bars per symbol/timeframe so a replay can use up to 2,000 completed bars while excluding the forming bar
- Strategy indicators are precomputed once for the replay history to keep larger backtests responsive
- Entry is modeled at the signal candle close; TP3 or stop loss exits are checked on following candles
- Ambiguous candles where both exit levels are touched conservatively assume stop loss first
- Spread, slippage, commissions, partial exits and portfolio risk are explicitly not modeled
- Backtesting does not submit orders; practice trades are separate and simulation-only
- Verification: 25 focused backtest-engine, analysis, API and practice-order tests pass; frontend lint and production build pass

## Multi-timeframe technical analysis

- Technical analysis API now returns weighted trend consensus and per-timeframe structure for M5 through D1
- Analytics page displays each interval's direction and structure alongside overall consensus
- This remains based on generated simulation candles and is clearly labeled as such

## Strategy catalogue

- Strategies page documents the implemented trend-following and breakout/retest entry rules
- Displays shared stop, reward/risk and expiry guardrails
- Links to signal generation and preselects the chosen strategy on the backtesting page
- No strategy is presented as an automated broker executor

## System health status

Status: real runtime health probes and dashboard status view implemented.

- Health endpoint probes PostgreSQL/SQLite database connectivity and Redis availability
- System page displays API, database, Redis, broker, MT5 worker, engine and live-trading state
- Status refreshes every 10 seconds and is read-only
- Live trading remains independently disabled and cannot be changed from the dashboard
- Health tests and frontend production build pass

## Automatic realtime signals

Status: server-side realtime scanning and browser history controls implemented.

- API scans configured symbols every 30 seconds while a broker account is connected
- Stable signal fingerprints deduplicate repeated generated setups
- Active and history views separate live validated setups from expired retained signals
- Signal history is persisted in PostgreSQL and deduplicated by stable candle-aware fingerprints
- Signals history refreshes every 15 seconds and remains read-only
- Simulation and MT5 source safeguards remain unchanged; no orders are submitted
- Signal engine/API tests pass
- Validated signals persist in PostgreSQL with stable-ID deduplication
- Alembic migration `20261123_003` creates the `trading_signals` history table

## Configurable risk policy

Status: policy values are environment-configured and displayed for safe operations.

- API exposes maximum daily/weekly loss, open-position count and aggregate open-risk policy
- Docker Compose provides defaults of 3%, 6%, 3 positions and 2% aggregate open risk
- Risk page retains a 0.1–1% per-trade control and prohibits Martingale/grid strategy modes
- Live trading permission remains independently disabled and cannot be changed from this page
- Focused risk tests, frontend lint and production build pass

## Configurable position risk

Status: implemented within the existing 1% maximum safety ceiling.

- Risk page exposes a 0.1–1% risk-per-trade control
- Backend recalculates the dollar risk budget and volume down to broker volume steps
- API rejects position sizing above 1% and keeps estimates read-only
- Focused risk API tests and frontend production build pass

## Telegram notifications

Status: configuration status and test delivery implemented.

- Notifications page reports whether Telegram environment credentials are configured
- Bot token is never returned to the browser; chat ID is masked
- Administrator can send a test message through the authenticated API
- Telegram delivery requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Docker Compose forwards both variables to the API container
- Focused notification API tests pass

## Read-only order activity

Status: implemented for open positions and completed broker deals.

- Orders page combines open position snapshots with raw completed deal activity
- Uses simulation or MT5 data from the existing positions and history APIs
- Refreshes every 15 seconds and identifies read-only simulation/MT5 data
- No order placement, modification or cancellation controls are exposed
- Frontend lint and production build pass

## MT5 historical candle feed

- Windows worker sends up to 501 OHLCV bars for each monitored symbol and supported timeframe, along with broker tick-size metadata
- Candle snapshots are refreshed once per minute and validated for OHLC consistency and chronological ordering
- Analysis and signal generation use broker candles while MT5 is selected; a disconnected or incomplete worker feed returns an explicit error instead of silently analyzing simulation data
- Backtesting uses up to 2,000 completed MT5 candles when the broker is selected; simulation candles require an explicitly connected simulation account
- Verification: full backend suite, frontend production build and focused lint passed
- Real broker history delivery still requires validating the updated worker on Windows with an installed MT5 terminal

## Authentication

Status: administrator sign-in and API session protection implemented.

- Provision the first administrator with `BOOTSTRAP_ADMIN_EMAIL` and a 12+ character `BOOTSTRAP_ADMIN_PASSWORD`; no public sign-up route is exposed
- Docker startup applies Alembic migrations and creates the administrator only when the configured email does not already exist
- Non-development deployments reject the default or short JWT signing secret
- The API issues an expiring HttpOnly, SameSite=Lax cookie; the browser reaches the API only through the same-origin Next.js proxy
- All versioned application APIs require a valid session; health, login/logout, and the separately token-authenticated MT5 worker endpoints are exempt
- Sign out clears the session cookie; login does not return the JWT to JavaScript

## Persistent runtime connection state

Status: broker and engine state survive API restarts and browser reloads.

- Simulation connection and engine state are stored in Redis without credentials
- MT5 configuration is restored and waits for a fresh Windows worker heartbeat
- Disconnect and engine stop/start actions update the persisted snapshot
- Broker API tests verify simulation/engine restore behavior

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
