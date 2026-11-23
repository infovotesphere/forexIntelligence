PROJECT: FOREX INTELLIGENCE

Automated Forex Trading, MT5 Integration & Performance Management Platform

You are acting as a senior software architect, senior Python developer, quantitative trading systems engineer, database architect, frontend engineer, DevOps engineer and cybersecurity specialist.

Your responsibility is to DESIGN, BUILD, TEST, DOCUMENT AND PREPARE a complete production-grade Forex trading automation platform called Forex Intelligence.

Do not merely provide explanations, code examples, recommendations or architectural diagrams. You must work directly inside the current GitHub Codespace repository, create the necessary directories and files, implement functional modules, configure the development environment, run tests, fix errors and maintain comprehensive documentation.

The result must be a working, modular, maintainable software application.

⸻

1. PROJECT OBJECTIVE

Build a full-stack automated Forex trading platform that connects to an Exness MetaTrader 5 (MT5) trading account.

The application must be capable of:

1. Monitoring Forex and Gold markets.
2. Analysing market trends and price movements.
3. Identifying potential trading opportunities.
4. Generating BUY and SELL signals.
5. Calculating entry prices, stop losses and multiple take-profit targets.
6. Calculating position sizes using account equity and risk percentage.
7. Automatically executing approved algorithmic trading strategies.
8. Monitoring and managing open positions.
9. Automatically modifying stop losses and take-profit levels when strategy rules require it.
10. Recording all trading signals, orders, executions, positions and results.
11. Calculating trading performance and generating reports.
12. Sending Telegram notifications.
13. Providing a professional web dashboard for monitoring and controlling the system.

The application must support both demo and live trading accounts.

DEMO TRADING MUST BE THE INITIAL AND DEFAULT ENVIRONMENT.

Live trading must remain disabled until the administrator explicitly enables it through a protected configuration and confirmation process.

Never enable live trading automatically.

⸻

2. USER REQUIREMENTS

Use the following requirements as fixed project specifications.

Broker: Exness.

Trading platform: MetaTrader 5.

Trading styles:

* Scalping.
* Day trading.
* Swing trading.

Trading instruments:

* Major Forex currency pairs.
* XAUUSD (Gold).

Initial currency pairs should include:

* EURUSD.
* GBPUSD.
* USDJPY.
* USDCHF.
* USDCAD.
* AUDUSD.
* NZDUSD.
* XAUUSD.

Do not assume that broker symbols always use these exact names. Discover the actual available symbols from MT5 and support broker suffixes and prefixes.

Risk per trade: 1% of account equity.

Initial proposed risk controls:

* Maximum daily loss: 3%.
* Maximum weekly loss: 6%.
* Maximum simultaneous positions: 3.
* Maximum aggregate open risk: 2%.
* Minimum strategy risk/reward target: 1:2.
* Martingale: prohibited.
* Grid trading: prohibited.
* Unprotected positions: prohibited.

All risk settings must be configurable through the administrative dashboard.

Development environment:

* GitHub Codespaces.
* Windows computer for MT5 integration and testing.
* Windows VPS for future continuous trading.

Frontend:

* React / Next.js.
* TypeScript.
* Responsive interface.

Backend:

* Python.
* FastAPI.

Database:

* PostgreSQL.
* SQLAlchemy.
* Alembic.

Background processing:

* Redis.
* Background worker.

Broker integration:

* Official MetaTrader5 Python package on Windows.
* A modular MT5 connector.
* A simulation adapter for Linux development and automated tests.

Notifications:

* Telegram Bot API.

⸻

3. MANDATORY ARCHITECTURAL PRINCIPLES

Implement a modular architecture.

The frontend, API, trading engine, broker connector, risk manager, database and notification services must remain logically independent.

The web application must not be responsible for directly executing trades.

The trading engine must operate independently of the web dashboard.

The trading engine must be capable of continuing its safety and position-monitoring functions if the frontend becomes unavailable.

The strategy engine must NEVER execute broker orders directly.

Every trade must pass through:

1. Signal validation.
2. Position sizing.
3. Risk validation.
4. Market-condition validation.
5. Execution validation.
6. Central order execution manager.
7. Broker response verification.
8. Position reconciliation.
9. Database recording.

Use dependency injection and well-defined interfaces.

Use UTC for internal timestamps. Convert to user-selected timezones for display.

Use Decimal or NUMERIC for financial calculations. Never rely on binary floating-point arithmetic for persisted monetary values.

Use structured logging.

Implement robust error handling and service health monitoring.

Use idempotency keys to prevent duplicate orders.

Never assume an order was executed simply because an execution request was submitted.

Reconcile local records with actual MT5 orders, positions and deals.

⸻

4. REQUIRED REPOSITORY STRUCTURE

Build and maintain the following structure:

forex-intelligence/
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   │   ├── login/
│   │   │   ├── dashboard/
│   │   │   ├── markets/
│   │   │   ├── signals/
│   │   │   ├── positions/
│   │   │   ├── orders/
│   │   │   ├── history/
│   │   │   ├── analytics/
│   │   │   ├── strategies/
│   │   │   ├── risk/
│   │   │   ├── backtesting/
│   │   │   ├── notifications/
│   │   │   ├── system/
│   │   │   └── settings/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── public/
│   │
│   └── api/
│       ├── app/
│       │   ├── api/v1/
│       │   ├── core/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   ├── repositories/
│       │   ├── middleware/
│       │   ├── websocket/
│       │   └── main.py
│       ├── migrations/
│       ├── tests/
│       └── requirements.txt
│
├── trading/
│   ├── engine/
│   │   ├── main.py
│   │   ├── scheduler.py
│   │   └── orchestrator.py
│   ├── connectors/
│   │   ├── base.py
│   │   ├── mt5/
│   │   │   ├── client.py
│   │   │   ├── account.py
│   │   │   ├── market_data.py
│   │   │   ├── orders.py
│   │   │   └── positions.py
│   │   └── simulation/
│   ├── analysis/
│   │   ├── indicators.py
│   │   ├── market_structure.py
│   │   ├── trend_analysis.py
│   │   ├── support_resistance.py
│   │   └── market_regime.py
│   ├── strategies/
│   │   ├── base.py
│   │   ├── trend_following.py
│   │   └── breakout_retest.py
│   ├── signals/
│   │   ├── generator.py
│   │   └── validator.py
│   ├── risk/
│   │   ├── position_sizing.py
│   │   ├── exposure.py
│   │   ├── limits.py
│   │   └── validation.py
│   ├── execution/
│   │   ├── order_manager.py
│   │   ├── position_manager.py
│   │   ├── reconciliation.py
│   │   └── idempotency.py
│   ├── backtesting/
│   ├── notifications/
│   │   └── telegram.py
│   └── tests/
│
├── shared/
│   ├── contracts/
│   ├── enums/
│   └── constants/
│
├── infrastructure/
│   ├── docker/
│   ├── windows/
│   ├── linux/
│   └── scripts/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── API.md
│   ├── TRADING_RULES.md
│   ├── MT5_INTEGRATION.md
│   ├── SECURITY.md
│   ├── DEPLOYMENT.md
│   ├── BACKTESTING.md
│   └── USER_GUIDE.md
│
├── tests/
├── .github/
│   └── workflows/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── LICENSE

You may add further directories when justified, but do not unnecessarily change the architecture.

⸻

5. FRONTEND AND USER INTERFACE

Create a premium, professional financial trading dashboard.

Design requirements:

* Modern institutional trading platform appearance.
* Dark-first design.
* Navy and charcoal surfaces.
* Clean typography.
* Green for positive financial performance.
* Red for negative performance.
* Neutral grey for secondary information.
* No excessive gradients.
* Consistent spacing and typography.
* Responsive desktop, tablet and iPad layouts.
* Functional navigation.
* Proper loading, empty and error states.
* Clear data visualisation.

Use reusable components.

Create a responsive sidebar navigation and a top navigation bar.

Include connection status, account mode and trading engine status.

Required dashboard pages

A. Main Dashboard

Display:

* Account balance.
* Account equity.
* Free margin.
* Used margin.
* Floating profit/loss.
* Today’s profit/loss.
* Weekly profit/loss.
* Monthly profit/loss.
* Total closed trades.
* Win rate.
* Profit factor.
* Maximum drawdown.
* Current open positions.
* Active trading strategies.
* MT5 connection status.
* Trading engine status.

Include:

* Equity curve.
* Daily profit/loss chart.
* Recent trades.
* Recent signals.
* Instrument performance.
* Risk utilisation.
* Trading activity timeline.

Dashboard figures must come from actual backend data, not hardcoded sample values.

If there is no trading data, display a meaningful empty state.

B. Market Scanner

Display monitored instruments.

Include:

* Symbol.
* Current bid.
* Current ask.
* Spread.
* Price change.
* Current trend.
* Volatility.
* Active timeframe.
* Latest signal.
* Market status.

Allow the administrator to activate or deactivate monitored instruments.

C. Trading Signals

Display:

* Symbol.
* Direction.
* Strategy.
* Entry price.
* Entry range.
* Stop loss.
* TP1.
* TP2.
* TP3.
* Risk/reward ratio.
* Proposed lot size.
* Timeframe.
* Signal quality score.
* Signal explanation.
* Creation time.
* Expiration time.
* Signal status.

Include filtering by symbol, direction, strategy, timeframe and status.

D. Open Positions

Display:

* Ticket.
* Symbol.
* Direction.
* Entry price.
* Current market price.
* Volume.
* Stop loss.
* Take profit.
* Floating P/L.
* Risk amount.
* Holding duration.

Provide protected controls to:

* Close position.
* Modify stop loss.
* Modify take profit.
* Partially close a position.

Record every manual intervention.

E. Orders

Display pending, accepted, rejected, partially filled, cancelled and completed orders.

F. Trade History

Display complete historical trading records.

Include filters:

* Date range.
* Instrument.
* Strategy.
* Direction.
* Winning/losing.
* Trading account.

G. Analytics

Provide:

* Win rate.
* Profit factor.
* Net profit.
* Gross profit.
* Gross loss.
* Average winning trade.
* Average losing trade.
* Expectancy.
* Maximum drawdown.
* Average holding duration.
* Consecutive wins.
* Consecutive losses.
* Return by instrument.
* Return by strategy.
* Return by timeframe.
* Return by trading session.

H. Strategy Management

Allow administrators to:

* Enable or disable strategies.
* Change indicator parameters.
* Configure timeframes.
* Configure entry conditions.
* Configure stop-loss methods.
* Configure take-profit methods.
* Configure minimum signal quality.
* Configure strategy-specific risk restrictions.

Maintain version history of strategy configurations.

I. Risk Management

Display:

* Risk per trade.
* Total open risk.
* Daily loss.
* Weekly loss.
* Current drawdown.
* Maximum permitted drawdown.
* Available margin.
* Maximum concurrent positions.
* Exposure by currency.

Allow configurable limits.

J. Backtesting

Allow users to:

* Select strategy.
* Select instrument.
* Select timeframe.
* Select historical date range.
* Configure strategy parameters.
* Execute historical tests.
* Compare strategies.
* View performance reports.

K. Settings

Include:

* User profile.
* Broker account management.
* Trading environment.
* Instruments.
* Trading schedules.
* Telegram settings.
* Risk configuration.
* System configuration.
* Security settings.

⸻

6. BACKEND AND API ARCHITECTURE

Use FastAPI with versioned REST endpoints.

Implement:

/api/v1/auth
/api/v1/dashboard
/api/v1/accounts
/api/v1/markets
/api/v1/signals
/api/v1/orders
/api/v1/positions
/api/v1/history
/api/v1/analytics
/api/v1/strategies
/api/v1/risk
/api/v1/backtesting
/api/v1/notifications
/api/v1/system
/api/v1/settings

Implement WebSocket endpoints for:

* Account updates.
* Market updates.
* Signal updates.
* Position updates.
* Execution updates.
* Engine status.

Use authentication and authorisation middleware.

Implement pagination, filtering and sorting.

Use Pydantic schemas for validation.

Use SQLAlchemy repositories and service-layer separation.

Implement consistent API error responses.

Generate OpenAPI documentation.

⸻

7. DATABASE ARCHITECTURE

Use PostgreSQL, SQLAlchemy and Alembic.

Create migrations for:

1. users
2. broker_accounts
3. trading_instruments
4. strategies
5. strategy_versions
6. trading_signals
7. signal_events
8. trade_orders
9. trade_positions
10. trade_deals
11. market_snapshots
12. risk_settings
13. risk_events
14. daily_performance
15. notification_settings
16. notification_logs
17. execution_events
18. system_events
19. audit_logs
20. backtest_runs
21. backtest_results

Requirements:

* UUID primary keys.
* Foreign-key relationships.
* Database constraints.
* Appropriate indexes.
* JSONB for structured metadata.
* NUMERIC for monetary values and prices.
* UTC timestamps.
* Unique broker ticket and deal references scoped appropriately to the account.
* Idempotency protection.
* Transaction-safe updates.

Do not store passwords as plaintext.

Do not store MT5 credentials unencrypted.

Implement secure credential handling.

Every trade must be traceable from its original signal through its orders, executions, positions and final outcome.

Support MT5 hedging and netting account modes. Do not assume that a broker position and an individual order represent the same entity.

⸻

8. MT5 BROKER INTEGRATION

This is a critical component.

Implement a broker abstraction interface.

Define methods for:

* connect()
* disconnect()
* connection_status()
* get_account_info()
* get_instruments()
* get_symbol_info()
* get_tick()
* get_historical_candles()
* get_open_positions()
* get_pending_orders()
* get_order_history()
* get_deal_history()
* calculate_profit()
* calculate_margin()
* check_order()
* submit_order()
* modify_position()
* close_position()
* partial_close_position()

Implement two adapters:

A. MT5Adapter

Use the official MetaTrader5 Python package.

It must run on Windows with the MT5 desktop terminal installed and running.

Implement:

* Terminal initialization.
* Account identification.
* Account login verification.
* Symbol discovery.
* Historical data retrieval.
* Tick retrieval.
* Instrument specification retrieval.
* Position retrieval.
* Order execution.
* Position modification.
* Position closing.
* Historical deal reconciliation.
* Connection recovery.

B. SimulationAdapter

Implement a broker simulation adapter for Linux development and Codespaces.

It must support:

* Simulated market prices.
* Simulated account balances.
* Simulated orders.
* Simulated positions.
* Simulated execution responses.
* Simulated stop-loss and take-profit events.

Never present simulated executions as real broker executions.

Mark every simulated record clearly.

Do not install or import the Windows-only MT5 package as a mandatory Linux dependency.

Create separate dependency files for Windows MT5 and Linux development.

Use the broker’s actual symbol specifications to determine:

* Contract size.
* Tick size.
* Tick value.
* Minimum volume.
* Maximum volume.
* Volume step.
* Price digits.
* Trading sessions.
* Execution restrictions.

Do not hardcode pip values or contract specifications.

⸻

9. MARKET ANALYSIS ENGINE

Implement technical indicators using reliable Python libraries or carefully tested calculations.

Required indicators:

* EMA 20.
* EMA 50.
* EMA 200.
* RSI 14.
* MACD.
* ATR 14.
* Bollinger Bands.
* ADX.
* Stochastic oscillator.

Implement price-action and market-structure analysis:

* Higher highs.
* Higher lows.
* Lower highs.
* Lower lows.
* Break of structure.
* Change of character.
* Support zones.
* Resistance zones.
* Breakout detection.
* Retest detection.
* Candlestick confirmation.

Implement market-regime classification:

* Trending.
* Ranging.
* High volatility.
* Low volatility.
* Uncertain.

Implement multi-timeframe analysis.

Initial timeframes:

* M5.
* M15.
* M30.
* H1.
* H4.
* D1.

Use completed candles for strategy decisions by default to avoid unstable signals from incomplete candles.

Support configurable signal expiration.

Detect stale market data.

Reject signals when required market information is unavailable or unreliable.

⸻

10. TRADING STRATEGIES

Build a strategy interface that allows additional strategies to be added without modifying the execution engine.

Initial strategies:

Strategy A: Trend Following

Use:

* EMA 50.
* EMA 200.
* RSI.
* MACD.
* Market structure.
* Support and resistance.
* ATR.

Entry rules should consider:

* Confirmed higher-timeframe direction.
* Pullback.
* Momentum confirmation.
* Price action.
* Valid stop-loss distance.

Do not enter solely because two moving averages cross.

Strategy B: Breakout and Retest

Identify:

* Significant support/resistance.
* Consolidation ranges.
* Confirmed breakout.
* Candle close beyond the level.
* Retest.
* Momentum confirmation.

Reject false breakouts.

Strategy selection

Use market-regime classification to determine which strategies are suitable for current conditions.

Prevent multiple strategies from independently opening duplicate positions for the same opportunity.

Implement strategy-specific performance tracking.

All strategy parameters must be configurable.

Do not claim strategies are profitable until they have been validated through out-of-sample and forward testing.

⸻

11. SIGNAL GENERATION

Each signal must include:

* Unique signal ID.
* Instrument.
* BUY or SELL.
* Strategy.
* Timeframe.
* Entry price or entry range.
* Stop loss.
* TP1.
* TP2.
* TP3.
* Risk/reward ratios.
* Recommended volume.
* Account risk amount.
* Signal quality score.
* Market regime.
* Technical justification.
* Creation timestamp.
* Expiration timestamp.
* Signal status.

Possible signal statuses:

* GENERATED.
* VALIDATED.
* REJECTED.
* EXPIRED.
* EXECUTION_PENDING.
* EXECUTED.
* CANCELLED.

Provide explanations for every rejected signal.

The signal quality score must be a deterministic score based on documented conditions. Do not misrepresent this score as a probability of winning.

⸻

12. RISK MANAGEMENT ENGINE

This module has the highest priority after broker connectivity.

Implement a central risk management service.

Default risk:

1% of current account equity per trade.

Position sizing must consider:

* Account equity.
* Risk percentage.
* Stop-loss distance.
* Tick size.
* Tick value.
* Contract size.
* Account currency.
* Conversion rates.
* Broker volume constraints.
* Commission estimates.
* Execution costs.

Use MT5 profit-calculation facilities where appropriate to verify estimated losses for the proposed volume.

Use broker specifications rather than assumptions.

Implement:

* Maximum daily loss.
* Maximum weekly loss.
* Maximum aggregate open risk.
* Maximum concurrent positions.
* Currency exposure restrictions.
* Correlation controls.
* Margin checks.
* Spread filters.
* Slippage limits.
* Duplicate-trade protection.
* Maximum consecutive losses.
* Emergency trading suspension.

Risk limits must be evaluated immediately before every order.

A failed risk check must prevent execution.

A trade must never be opened without a valid protective stop loss.

If a broker cannot accept the required protective stop, do not silently open an unprotected position.

Never increase lot sizes after losses.

Never use martingale.

Never use unrestricted averaging down.

Never automatically disable protective risk limits.

Implement an emergency STOP ALL NEW TRADES control.

Existing open positions must remain protected and monitored after new trading has been suspended.

⸻

13. ORDER EXECUTION AND POSITION MANAGEMENT

Implement a central order execution manager.

Before submitting an order:

1. Verify MT5 connectivity.
2. Verify account identity.
3. Verify the trading environment.
4. Verify symbol availability.
5. Verify fresh tick data.
6. Verify market trading hours.
7. Verify spread.
8. Calculate proposed position size.
9. Check margin requirements.
10. Revalidate risk limits.
11. Check for duplicate orders.
12. Submit the request.
13. Inspect the actual broker response.
14. Confirm the resulting position or order.
15. Record all broker identifiers.

Handle:

* Market orders.
* Pending orders where supported.
* Partial fills.
* Requotes.
* Rejections.
* Invalid volume.
* Insufficient margin.
* Invalid stops.
* Market closure.
* Network interruption.
* Duplicate execution requests.

Implement:

* Stop-loss management.
* Take-profit management.
* Partial profit taking.
* Break-even movement.
* ATR-based trailing stops.
* Time-based exits.
* Strategy invalidation exits.

Never assume TP1, TP2 and TP3 are separate broker-supported targets on one position.

Implement partial-close logic or separate positions according to the broker’s account mode and execution rules.

Use reconciliation to resolve uncertain execution outcomes before attempting a retry.

⸻

14. TRADING JOURNAL AND PERFORMANCE ENGINE

Record all trading activities.

The system must maintain:

* Generated signals.
* Accepted signals.
* Rejected signals.
* Submitted orders.
* Broker order responses.
* Executed deals.
* Open positions.
* Closed positions.
* Partial closes.
* Stop-loss changes.
* Take-profit changes.
* Commissions.
* Swaps.
* Slippage.
* Net profit/loss.

Calculate:

* Total trades.
* Winning trades.
* Losing trades.
* Breakeven trades.
* Win rate.
* Gross profit.
* Gross loss.
* Net profit.
* Profit factor.
* Expectancy.
* Average reward/risk.
* Maximum drawdown.
* Average holding time.
* Consecutive winning trades.
* Consecutive losing trades.
* Return per instrument.
* Return per strategy.
* Return per timeframe.
* Return per session.

Ensure performance is calculated from actual broker deal history.

Avoid double-counting partial executions.

Clearly distinguish realised profit/loss from floating profit/loss.

Provide daily, weekly, monthly, yearly and custom date-range reports.

⸻

15. TELEGRAM NOTIFICATIONS

Integrate Telegram Bot API.

Support:

* Bot token configuration.
* Chat ID configuration.
* Connection testing.
* Message templates.
* Notification preferences.
* Notification history.

Send notifications for:

* Engine startup.
* Engine shutdown.
* MT5 disconnection.
* MT5 reconnection.
* New signal.
* Signal rejection.
* Confirmed order execution.
* Trade modification.
* Partial close.
* Stop loss hit.
* Take profit hit.
* Daily loss threshold reached.
* Weekly loss threshold reached.
* Trading suspended.
* Critical system error.
* Daily performance report.

Include symbol, direction, entry, SL, TP, volume and risk amount when appropriate.

Do not send duplicate notifications.

Telegram must not be treated as an unauthenticated order execution interface.

Never expose bot tokens in logs or frontend responses.

⸻

16. BACKTESTING ENGINE

Implement a historical backtesting framework.

Requirements:

* Historical candle input.
* Configurable strategy.
* Configurable timeframe.
* Configurable instruments.
* Historical spread modelling.
* Commission modelling.
* Swap modelling where relevant.
* Slippage modelling.
* Position sizing.
* Stop-loss and take-profit simulation.
* Partial exits.
* Drawdown calculations.
* Equity curve.

Support:

* In-sample testing.
* Out-of-sample testing.
* Walk-forward analysis.
* Parameter comparison.

Avoid look-ahead bias and survivorship bias.

Use realistic execution assumptions.

Do not use future candle data to generate past signals.

Display limitations of candle-based simulations, particularly where intrabar stop-loss and take-profit ordering is ambiguous.

Every backtest must record its strategy version and configuration.

⸻

17. SECURITY AND ACCOUNT PROTECTION

Implement:

* Secure password hashing.
* Authentication.
* Role-based permissions.
* Session management.
* CSRF protection where applicable.
* Input validation.
* Rate limiting.
* Secure CORS configuration.
* Encrypted broker credentials.
* Secrets management.
* Audit logs.
* Database backups.
* Authentication event logs.

The application must support separate demo and live account configurations.

Do not mix demo and live trade records.

Never display full broker passwords or API secrets.

Never commit .env files.

Live trading must require:

* Administrator authorisation.
* Correct account identity.
* Explicit live environment selection.
* A separate live-trading enable switch.
* A visible confirmation step.
* All risk controls active.

Keep live trading disabled by default in code and database configuration.

⸻

18. DEPLOYMENT ARCHITECTURE

The final deployment must use two environments.

Linux server

Hosts:

* Next.js frontend.
* FastAPI.
* PostgreSQL.
* Redis.
* Background workers.
* Monitoring services.

Windows VPS

Hosts:

* Exness MT5 desktop terminal.
* Python MT5 integration worker.
* Trading engine.
* Execution manager.
* Position manager.

The Windows worker should establish authenticated outbound communication with the backend.

Do not expose MT5 terminal ports or Windows Remote Desktop publicly.

Create:

* Docker Compose configuration.
* Windows installation scripts.
* Windows service or supervised worker configuration.
* Linux deployment scripts.
* Environment templates.
* Health checks.
* Backup procedures.
* Restart procedures.
* Monitoring documentation.

The trading engine must recover safely after a restart.

After restart, reconcile existing broker positions before allowing new trades.

Never blindly repeat orders after a crash.

⸻

19. DEVELOPMENT ENVIRONMENT

The primary development environment is GitHub Codespaces.

Use:

* Python 3.11.
* Node.js LTS.
* PostgreSQL 16.
* Redis 7.
* Docker Compose.
* TypeScript.
* FastAPI.
* SQLAlchemy.
* Alembic.

Use the official MetaTrader5 package only in the Windows-specific environment.

Create separate dependency files for:

* Linux backend.
* Windows trading worker.
* Frontend.

The Linux development environment must work without the actual MT5 terminal.

Use SimulationAdapter for automated testing.

Create an .env.example file with all required configuration keys.

Never place actual credentials in source files.

⸻

20. TESTING REQUIREMENTS

Write automated tests for all critical components.

Include:

Backend tests

* Authentication.
* Database operations.
* API endpoints.
* Input validation.
* Authorisation.
* Pagination.
* Error handling.

Trading engine tests

* Indicator calculations.
* Market analysis.
* Strategy evaluation.
* Signal validation.
* Position sizing.
* Risk restrictions.
* Duplicate prevention.
* Order management.
* Position reconciliation.

Broker tests

* Simulation connection.
* Account information.
* Price retrieval.
* Order submission.
* Order rejection.
* Position updates.
* Disconnection and recovery.

Performance tests

* Partial executions.
* Multiple deals per position.
* Commission calculations.
* Swap calculations.
* Realised and floating P/L.
* Daily performance aggregation.

Do not use real-money trading for automated tests.

Do not allow tests to connect to a live Exness account.

All test execution must use mocks or SimulationAdapter.

⸻

21. IMPLEMENTATION STRATEGY

Build the application incrementally.

Do not attempt to generate the entire system in one enormous, untested implementation.

Follow these development milestones.

PHASE 1 — FOUNDATION

Implement:

* Repository structure.
* Next.js frontend.
* FastAPI backend.
* PostgreSQL.
* Redis.
* SQLAlchemy.
* Alembic.
* Environment configuration.
* Authentication foundation.
* Health checks.
* Initial dashboard shell.
* Automated tests.
* Documentation.

Acceptance criteria:

* Frontend starts.
* Backend starts.
* Database connects.
* Migrations execute.
* Redis responds.
* Health endpoints work.
* Initial tests pass.

PHASE 2 — MT5 CONNECTIVITY

Implement:

* MT5 connector interface.
* Windows MT5 adapter.
* Simulation adapter.
* Account monitoring.
* Instrument discovery.
* Market data retrieval.
* Historical candle retrieval.
* Connection monitoring.

Acceptance criteria:

* Demo account can connect from Windows.
* Account details are retrieved.
* Available symbols are discovered.
* Historical data can be retrieved.
* Codespaces can use simulation mode.
* No live orders are placed.

PHASE 3 — MARKET ANALYSIS

Implement:

* Technical indicators.
* Market structure.
* Trend analysis.
* Market regime.
* Multi-timeframe analysis.
* Strategy interfaces.

Acceptance criteria:

* Historical candles are analysed.
* Indicator results are validated.
* Strategy conditions can be evaluated.
* Analysis results are recorded.

PHASE 4 — SIGNAL GENERATION

Implement:

* Trend-following strategy.
* Breakout-and-retest strategy.
* Signal scoring.
* Entry calculation.
* Stop-loss calculation.
* Multiple take-profit calculations.
* Signal expiration.
* Signal validation.

Acceptance criteria:

* Valid signals are generated.
* Invalid signals are rejected.
* Every decision is recorded.
* No orders are submitted.

PHASE 5 — RISK MANAGEMENT

Implement:

* Position sizing.
* Instrument-specific calculations.
* Account-level risk controls.
* Daily and weekly loss limits.
* Exposure monitoring.
* Spread restrictions.
* Margin validation.

Acceptance criteria:

* Lot sizes are calculated correctly.
* Risk checks reject unsafe trades.
* Risk limits cannot be bypassed by strategy modules.

PHASE 6 — DEMO EXECUTION

Implement:

* Automatic demo execution.
* Order manager.
* Position manager.
* Broker reconciliation.
* Partial closes.
* Stop-loss management.
* Take-profit management.
* Emergency trading suspension.

Acceptance criteria:

* Only the configured demo account is used.
* Orders are confirmed against broker records.
* Actual positions are reconciled.
* All execution events are recorded.
* Restart recovery works.
* Live trading remains disabled.

PHASE 7 — DASHBOARD AND ANALYTICS

Complete all dashboard pages.

Implement:

* Live account updates.
* Market scanner.
* Signals.
* Orders.
* Open positions.
* Trade history.
* Performance analytics.
* Risk dashboard.
* Strategy management.
* Telegram notifications.

Acceptance criteria:

* Dashboard data comes from actual backend records.
* WebSocket updates work.
* Analytics reconcile with broker history.
* Notifications are delivered correctly.

PHASE 8 — BACKTESTING

Implement historical strategy validation.

Acceptance criteria:

* Backtests can be run.
* Results are persisted.
* Out-of-sample testing is supported.
* Performance reports are generated.
* Look-ahead bias tests are included.

PHASE 9 — WINDOWS VPS DEPLOYMENT

Prepare:

* Windows VPS installation.
* MT5 terminal setup.
* Python worker installation.
* Secure backend communication.
* Automatic recovery.
* Logging.
* Monitoring.

PHASE 10 — CONTROLLED LIVE ACTIVATION

Do not activate automatically.

Require explicit administrator approval after:

* Successful integration tests.
* Successful demo execution tests.
* Strategy backtesting.
* Forward testing.
* Risk validation.
* Reconciliation validation.
* Recovery testing.
* Security review.

⸻

22. CODING STANDARDS

Follow these requirements throughout development.

1. Write clean, maintainable and modular code.
2. Use meaningful class, function and variable names.
3. Use type hints in Python.
4. Use Pydantic validation.
5. Use TypeScript strictly.
6. Avoid unnecessary code duplication.
7. Keep business logic outside API route handlers.
8. Keep trading strategies independent of broker integration.
9. Centralise financial calculations.
10. Write tests for financial and trading calculations.
11. Use database transactions appropriately.
12. Handle exceptions explicitly.
13. Add structured logs.
14. Document complex trading logic.
15. Avoid hardcoded secrets.
16. Avoid fake data in production dashboard views.
17. Never use placeholder implementations for critical financial calculations.
18. Do not silently ignore errors.
19. Do not claim an integration is complete unless it has been tested.
20. Do not remove existing working functionality without justification.

Before adding a dependency, check whether an existing dependency already provides the required functionality.

Keep requirements files and lockfiles updated.

⸻

23. IMPORTANT EXECUTION INSTRUCTIONS FOR YOU

You are operating inside an actual GitHub Codespace.

Start by inspecting the current repository:

* Determine whether it is empty.
* Identify existing files.
* Inspect the current Python version.
* Inspect the Node.js version.
* Inspect Docker availability.
* Inspect existing configurations.

Preserve useful existing work.

Do not blindly overwrite files.

Then proceed as follows:

1. Create a concise implementation plan.
2. Create the project structure.
3. Implement Phase 1 completely.
4. Install dependencies.
5. Configure PostgreSQL and Redis.
6. Create database models and migrations.
7. Implement the FastAPI application.
8. Implement the Next.js dashboard shell.
9. Implement authentication foundations.
10. Create automated tests.
11. Start the services.
12. Run the tests.
13. Fix errors.
14. Verify the application endpoints.
15. Update the README.
16. Document the exact setup and startup commands.

Do not stop after generating the plan.

Do not ask me to manually create files that you can create yourself.

Do not fabricate test results.

If a tool, service or external credential is unavailable, implement the appropriate interface and document the remaining configuration requirement.

If a task cannot be completed in Codespaces because it requires Windows MT5, implement the Windows-specific module separately and provide the precise Windows setup instructions.

Complete Phase 1 before proceeding to Phase 2.

Do not attempt live broker execution during initial development.

Do not automatically proceed to live trading.

At the end of each phase, provide:

* Files created.
* Files modified.
* Modules implemented.
* Dependencies installed.
* Database migrations created.
* Tests executed.
* Test results.
* Outstanding issues.
* Manual configuration still required.
* Exact commands for starting the application.
* The next recommended development milestone.

Maintain a DEVELOPMENT_STATUS.md file and update it as implementation progresses.

If a phase has outstanding failures, report them honestly and fix them before declaring that phase complete.

⸻

24. FINAL ACCEPTANCE CRITERIA

The completed platform must provide:

1. A professional, responsive web application.
2. Secure user authentication.
3. PostgreSQL-backed persistent records.
4. Working FastAPI backend.
5. MT5 integration on Windows.
6. Simulation support in Codespaces.
7. Automated market analysis.
8. Trading signal generation.
9. Risk-based position sizing.
10. Automated demo trade execution.
11. Stop-loss and take-profit management.
12. Complete trading journal.
13. Performance analytics.
14. Telegram notifications.
15. Historical backtesting.
16. Administrative risk controls.
17. Secure demo/live separation.
18. Deployment documentation.
19. Automated testing.
20. Restart recovery and broker reconciliation.

The application must be maintainable, extensible and suitable for future commercial-grade development.

BEGIN NOW BY INSPECTING THE CURRENT CODESPACE REPOSITORY AND IMPLEMENTING PHASE 1.

---

# Phase 1 implementation

## Start locally

Use Docker for the recommended complete environment:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Open on an iPad with GitHub Codespaces

Do not open `localhost` on the iPad; that address refers to the iPad itself. In Codespaces, open the **Ports** tab and use **Open in Browser** for port `3000`. If prompted, keep ports private/authenticated. Dashboard API requests use a same-origin frontend proxy, so you only need to open port `3000` in the iPad browser; port `8000` does not need to be opened separately.

Run the backend directly in Codespaces:

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend directly:

```bash
cd apps/web
npm install
npm run dev
```

Live trading is disabled by default. No MT5 package or live credentials are required for Phase 1.

## MT5 account connections

The Settings page supports MT5 demo and live-account connections. A live account requires an explicit read-only confirmation and is for account/market monitoring only. Live trading remains disabled; the Windows connector rejects broker order submission and position changes. A Windows MT5 terminal/worker and backend encryption/worker secrets are required. See [MT5 integration](./docs/MT5_INTEGRATION.md).

Your priority is to produce a working foundation, not merely a collection of generated source files.

How to use this prompt in Codespaces

* Open your forex-intelligence repository in Codespaces.
* Open GitHub Copilot Chat.
* Switch to Agent mode, not Ask mode.
* Paste the complete master prompt above.
* Allow the agent to inspect and modify the repository.
* Review proposed terminal commands, especially installations and database operations.
* Let it complete Phase 1 and verify the results.

Important: Don’t let Copilot rush the trading engine

I recommend the following development gates:

Gate	What must work before proceeding
1	Frontend, API and database
2	Real MT5 demo connection
3	Market analysis and signals
4	Position sizing and risk validation
5	Demo order execution
6	Performance reconciliation
7	Backtesting and forward testing
8	Production deployment

My strongest recommendation: Build the complete infrastructure first, then connect your Exness demo account. The most important thing is to ensure that the bot can correctly calculate risk, place protective orders, recognise actual executions and recover safely after interruptions before it is allowed to trade automatically.