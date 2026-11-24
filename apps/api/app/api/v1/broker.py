import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, SecretStr, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.contracts.broker import Candle
from app.core.broker import cache_simulation_market_candle, get_live_mt5_tick, simulation_adapter
from app.core.config import get_settings
from app.core.credential_encryption import CredentialEncryptionError, decrypt_credentials, encrypt_credentials
from app.core.database import get_db
from app.core.market_data import get_mt5_candles
from app.core.persistent_runtime import save_runtime_state
from app.core.real_market_data import get_real_market_candles
from app.core.runtime import runtime_store
from app.models.trade_deal import TradeDeal

router = APIRouter(tags=["broker"])


class DemoConnectRequest(BaseModel):
    broker: str = Field(default="simulation", pattern="^(simulation|mt5)$")
    environment: str = Field(default="demo", pattern="^(demo|live)$")
    live_read_only_confirmed: bool = False
    account_id: str | None = Field(default=None, pattern="^[0-9]{1,20}$")
    password: SecretStr | None = Field(default=None, max_length=255, repr=False)
    server: str | None = Field(default=None, max_length=255)


class SimulationOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    direction: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "BUY_STOP", "SELL_STOP"] = "MARKET"
    volume: Decimal = Field(gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_order_type(self) -> "SimulationOrderRequest":
        if self.order_type == "MARKET" and self.stop_price is not None:
            raise ValueError("Market orders cannot specify a stop entry price")
        if self.order_type != "MARKET" and self.stop_price is None:
            raise ValueError("Buy stop and sell stop orders require an entry price")
        if self.order_type == "BUY_STOP" and self.direction != "BUY":
            raise ValueError("Buy stop orders must use the BUY direction")
        if self.order_type == "SELL_STOP" and self.direction != "SELL":
            raise ValueError("Sell stop orders must use the SELL direction")
        return self


class PracticeDepositRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class ModifySimulationPositionRequest(BaseModel):
    stop_loss: Decimal = Field(ge=0)
    take_profit: Decimal = Field(ge=0)


class CloseSimulationPositionsRequest(BaseModel):
    tickets: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_tickets(self) -> "CloseSimulationPositionsRequest":
        if len(set(self.tickets)) != len(self.tickets):
            raise ValueError("A position can only be selected once")
        return self


@router.post("/accounts/connect")
def connect_account(payload: DemoConnectRequest) -> dict:
    if payload.broker == "simulation":
        if payload.environment != "demo":
            raise HTTPException(status_code=422, detail="Simulation accounts only support the demo environment")
        state = runtime_store.connect_demo()
    else:
        if not payload.account_id or not payload.password or not payload.server:
            raise HTTPException(status_code=422, detail="MT5 login, password and server are required")
        if payload.environment == "live" and not payload.live_read_only_confirmed:
            raise HTTPException(
                status_code=422,
                detail="Confirm that this live MT5 account is for read-only monitoring and paper trading only",
            )
        try:
            encrypted = encrypt_credentials(json.dumps({
                "account_id": payload.account_id,
                "password": payload.password.get_secret_value(),
                "server": payload.server,
                "environment": payload.environment,
            }).encode("utf-8"))
        except CredentialEncryptionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        state = runtime_store.configure_mt5_account(
            payload.account_id,
            payload.server,
            payload.environment,
            encrypted,
        )
    save_runtime_state()
    return {
        "connected": state.mt5_connected,
        "environment": state.environment,
        "broker": state.broker,
        "account_id": state.account_id,
        "engine_running": state.engine_running,
        "live_trading_enabled": False,
        "simulated": state.broker == "simulation",
        "trading_mode": "paper_only",
        "message": state.message,
    }


@router.post("/accounts/disconnect")
def disconnect_account() -> dict:
    state = runtime_store.disconnect()
    save_runtime_state()
    return {"connected": False, "environment": "demo", "broker": state.broker, "account_id": "",
            "engine_running": False, "live_trading_enabled": False, "simulated": False,
            "message": state.message}


def require_worker(authorization: str | None = Header(default=None)) -> None:
    expected = get_settings().mt5_worker_token
    if not expected:
        raise HTTPException(status_code=503, detail="MT5_WORKER_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Worker bearer token required")
    supplied = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid worker token")


class WorkerOpenPosition(BaseModel):
    ticket: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    direction: Literal["BUY", "SELL"]
    volume: Decimal = Field(gt=0)
    price_open: Decimal = Field(ge=0)
    price_current: Decimal = Field(ge=0)
    profit: Decimal
    stop_loss: Decimal = Field(ge=0)
    take_profit: Decimal = Field(ge=0)
    simulated: bool = False


class WorkerDealSnapshot(BaseModel):
    ticket: str = Field(min_length=1, max_length=64)
    order: str = Field(max_length=64)
    symbol: str = Field(max_length=32)
    direction: Literal["BUY", "SELL", "OTHER"]
    volume: Decimal = Field(ge=0)
    price: Decimal = Field(ge=0)
    profit: Decimal
    commission: Decimal
    swap: Decimal
    time: datetime
    simulated: bool = False

    @model_validator(mode="after")
    def validate_deal_time(self) -> "WorkerDealSnapshot":
        if self.time.tzinfo is None or self.time.utcoffset() is None:
            raise ValueError("Deal timestamps must include a timezone")
        return self


class WorkerCandle(BaseModel):
    time: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self) -> "WorkerCandle":
        if self.time.tzinfo is None or self.time.utcoffset() is None:
            raise ValueError("Candle timestamps must include a timezone")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close) or self.low > self.high:
            raise ValueError("Candle prices must satisfy low <= open/close <= high")
        return self


class WorkerCandleSnapshot(BaseModel):
    base_symbol: str = Field(min_length=1, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    symbol: str = Field(min_length=1, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    timeframe: Literal["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
    candles: list[WorkerCandle] = Field(min_length=2, max_length=2001)

    @model_validator(mode="after")
    def validate_chronological_order(self) -> "WorkerCandleSnapshot":
        if any(previous.time >= current.time for previous, current in zip(self.candles, self.candles[1:])):
            raise ValueError("Candle timestamps must be strictly increasing")
        return self


class WorkerStatusUpdate(BaseModel):
    connected: bool
    account_id: str = Field(min_length=1, max_length=64)
    server: str = Field(min_length=1, max_length=255)
    environment: str = Field(pattern="^(demo|live)$")
    currency: str = Field(default="", max_length=16)
    balance: Decimal | None = None
    equity: Decimal | None = None
    message: str = Field(max_length=500)
    market_data: list[dict] = Field(default_factory=list, max_length=32)
    market_candles: list[WorkerCandleSnapshot] = Field(default_factory=list, max_length=64)
    open_positions: list[WorkerOpenPosition] = Field(default_factory=list, max_length=500)
    history_deals: list[WorkerDealSnapshot] = Field(default_factory=list, max_length=500)


def _format_decimal(value: Decimal) -> str:
    if value.is_zero():
        return "0"
    return format(value.normalize(), "f")


@router.post("/worker/mt5/claim", response_model=None)
def claim_mt5_credentials(authorization: str | None = Header(default=None)) -> dict | Response:
    require_worker(authorization)
    encrypted = runtime_store.claim_mt5_credentials()
    if encrypted is None:
        return Response(status_code=204)
    try:
        credentials = json.loads(decrypt_credentials(encrypted))
    except (CredentialEncryptionError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Unable to decrypt queued MT5 credentials") from exc
    return credentials


@router.post("/worker/mt5/status", dependencies=[Depends(require_worker)])
def update_mt5_status(
    payload: WorkerStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    configured = runtime_store.state
    if (
        configured.broker != "mt5"
        or configured.account_id != payload.account_id
        or configured.server != payload.server
        or configured.environment != payload.environment
    ):
        raise HTTPException(status_code=409, detail="Worker status does not match the configured MT5 account")
    if payload.connected and payload.history_deals:
        tickets = {deal.ticket for deal in payload.history_deals}
        existing_tickets = set(db.scalars(
            select(TradeDeal.ticket).where(
                TradeDeal.account_id == payload.account_id,
                TradeDeal.server == payload.server,
                TradeDeal.environment == payload.environment,
                TradeDeal.ticket.in_(tickets),
            )
        ).all())
        new_deals = []
        for deal in payload.history_deals:
            if deal.ticket in existing_tickets:
                continue
            existing_tickets.add(deal.ticket)
            new_deals.append(
                TradeDeal(
                    account_id=payload.account_id,
                    server=payload.server,
                    environment=payload.environment,
                    ticket=deal.ticket,
                    order_ticket=deal.order,
                    symbol=deal.symbol,
                    direction=deal.direction,
                    volume=deal.volume,
                    price=deal.price,
                    profit=deal.profit,
                    commission=deal.commission,
                    swap=deal.swap,
                    deal_time=deal.time,
                    simulated=deal.simulated,
                )
            )
        if new_deals:
            db.add_all(new_deals)
            db.commit()
    try:
        state = runtime_store.update_mt5_status(
            connected=payload.connected,
            account_id=payload.account_id,
            server=payload.server,
            environment=payload.environment,
            currency=payload.currency,
            balance=payload.balance,
            equity=payload.equity,
            message=payload.message,
            market_data=payload.market_data,
            market_candles=[snapshot.model_dump(mode="json") for snapshot in payload.market_candles],
            open_positions=[position.model_dump(mode="json") for position in payload.open_positions],
            history_deals=[deal.model_dump(mode="json") for deal in payload.history_deals],
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "connected": state.mt5_connected,
        "environment": state.environment,
        "live_trading_enabled": False,
        "trading_mode": "paper_only",
    }


@router.get("/engine/status")
def engine_status() -> dict:
    state = runtime_store.state
    connected = runtime_store.broker_connected()
    return {"running": state.engine_running and connected, "broker_connected": connected,
            "environment": state.environment, "live_trading_enabled": False,
            "message": (
                "Windows MT5 worker heartbeat timed out"
                if state.broker == "mt5" and state.mt5_connected and not connected
                else state.message
            )}


@router.post("/engine/start")
def start_engine() -> dict:
    state = runtime_store.start_engine()
    save_runtime_state()
    return {"running": state.engine_running, "broker_connected": runtime_store.broker_connected(),
            "environment": state.environment, "live_trading_enabled": False,
            "message": state.message}


@router.post("/engine/stop")
def stop_engine() -> dict:
    state = runtime_store.stop_engine()
    save_runtime_state()
    return {"running": False, "broker_connected": runtime_store.broker_connected(),
            "environment": state.environment, "live_trading_enabled": False,
            "message": state.message}


@router.get("/accounts")
def accounts() -> dict:
    state = runtime_store.state
    if state.broker == "mt5":
        return {
            "account_id": state.account_id,
            "broker": "mt5",
            "environment": state.environment,
            "currency": state.account_currency,
            "balance": None if state.balance is None else str(state.balance),
            "equity": None if state.equity is None else str(state.equity),
            "simulated": False,
            "broker_data_live": True,
            "trading_mode": "paper_only",
            "server": state.server,
            "connected": runtime_store.broker_connected(),
        }
    if not state.mt5_connected:
        raise HTTPException(status_code=409, detail="No broker account is connected")
    account = simulation_adapter.get_account_info()
    return {
        "account_id": account.account_id,
        "broker": account.broker,
        "environment": account.environment,
        "currency": account.currency,
        "balance": str(account.balance),
        "equity": str(account.equity),
        "margin": str(account.margin),
        "free_margin": str(account.free_margin),
        "margin_level": None if account.margin_level is None else str(account.margin_level),
        "simulated": account.simulated,
    }


@router.get("/accounts/status")
def account_status() -> dict:
    state = runtime_store.state
    connected = runtime_store.broker_connected()
    account = simulation_adapter.get_account_info() if state.broker == "simulation" and state.mt5_connected else None
    return {
        "connected": connected,
        "environment": state.environment,
        "broker": state.broker,
        "account_id": state.account_id,
        "engine_running": state.engine_running,
        "live_trading_enabled": False,
        "simulated": state.broker == "simulation",
        "message": (
            "Windows MT5 worker heartbeat timed out"
            if state.broker == "mt5" and state.mt5_connected and not connected
            else state.message
        ),
        "account": (
            {
                "account_id": account.account_id,
                "currency": account.currency,
                "balance": str(account.balance),
                "equity": str(account.equity),
            } if account is not None else {
                "account_id": state.account_id,
                "currency": state.account_currency,
                "balance": None if state.balance is None else str(state.balance),
                "equity": None if state.equity is None else str(state.equity),
            } if state.broker == "mt5" else None
        ),
        "trading_mode": "paper_only",
    }


@router.get("/markets")
def markets() -> list[dict]:
    state = runtime_store.state
    if state.broker == "mt5":
        if not runtime_store.broker_connected():
            return []
        return [
            {
                **quote,
                "spread": str(Decimal(str(quote["ask"])) - Decimal(str(quote["bid"]))),
                "simulated": False,
                "execution_mode": "paper_only",
            }
            for quote in state.market_data
        ]
    instruments = []
    for instrument in simulation_adapter.get_instruments():
        tick = simulation_adapter.get_tick(instrument.symbol)
        instruments.append({
            "symbol": instrument.symbol,
            "description": instrument.description,
            "bid": str(tick.bid),
            "ask": str(tick.ask),
            "spread": str(tick.ask - tick.bid),
            "time": tick.time.isoformat(),
            "digits": instrument.digits,
            "contract_size": str(instrument.contract_size),
            "tick_size": str(instrument.tick_size),
            "tick_value": str(instrument.tick_value),
            "minimum_volume": str(instrument.minimum_volume),
            "maximum_volume": str(instrument.maximum_volume),
            "volume_step": str(instrument.volume_step),
            "digits": instrument.digits,
            "trade_allowed": instrument.trade_allowed,
            "simulated": True,
        })
    return instruments


@router.get("/markets/{symbol}/candles")
def market_candles(
    symbol: str,
    timeframe: Literal["M1", "M5", "M15", "M30", "H1", "H4", "D1"] = "M5",
    limit: int = Query(default=300, ge=30, le=2000),
) -> dict:
    state = runtime_store.state
    normalized_symbol = symbol.upper()
    if state.broker == "mt5":
        if not runtime_store.broker_connected():
            raise HTTPException(
                status_code=503,
                detail="MT5 broker prices are unavailable; connect the Windows worker.",
            )
        snapshot = get_mt5_candles(normalized_symbol, timeframe)
        if snapshot is None:
            raise HTTPException(
                status_code=503,
                detail=f"No fresh MT5 {timeframe} candle history is available for {normalized_symbol}",
            )
        actual_symbol, candles = snapshot
        try:
            tick = get_live_mt5_tick(normalized_symbol)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if tick is None:
            raise HTTPException(status_code=503, detail=f"No MT5 live quote is available for {normalized_symbol}")

        interval_seconds = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}[timeframe]
        candle_time = datetime.fromtimestamp(
            int(tick.time.timestamp() // interval_seconds) * interval_seconds,
            UTC,
        )
        live_price = (tick.bid + tick.ask) / Decimal("2")
        latest = candles[-1]
        if tick.time < latest.time:
            raise HTTPException(status_code=503, detail=f"The MT5 quote for {normalized_symbol} predates its candle history")
        if candle_time > latest.time:
            candles.append(Candle(
                symbol=actual_symbol,
                timeframe=timeframe,
                time=candle_time,
                open=live_price,
                high=max(tick.bid, tick.ask),
                low=min(tick.bid, tick.ask),
                close=live_price,
                volume=Decimal("0"),
            ))
        else:
            candles[-1] = Candle(
                symbol=latest.symbol,
                timeframe=latest.timeframe,
                time=latest.time,
                open=latest.open,
                high=max(latest.high, tick.bid, tick.ask),
                low=min(latest.low, tick.bid, tick.ask),
                close=live_price,
                volume=latest.volume,
            )
        quote_time = tick.time.isoformat()
    else:
        try:
            candles = get_real_market_candles(
                normalized_symbol,
                timeframe,
                cache_ttl=timedelta(seconds=3),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        actual_symbol = normalized_symbol
        try:
            cache_simulation_market_candle(normalized_symbol, candles[-1])
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        quote_time = candles[-1].time.isoformat()

    return {
        "symbol": actual_symbol,
        "timeframe": timeframe,
        "data_source": "mt5" if state.broker == "mt5" else "real_market",
        "simulated": state.broker != "mt5",
        "quote_time": quote_time,
        "candles": [
            {
                "time": candle.time.isoformat(),
                "open": str(candle.open),
                "high": str(candle.high),
                "low": str(candle.low),
                "close": str(candle.close),
                "volume": str(candle.volume),
            }
            for candle in candles[-limit:]
        ],
    }


@router.get("/practice/status")
def practice_status() -> dict:
    state_before_refresh = simulation_adapter.export_state()
    account = simulation_adapter.get_account_info()
    if simulation_adapter.export_state() != state_before_refresh:
        save_runtime_state()
    return {
        "connected": True,
        "simulated": True,
        "trading_mode": "paper_only",
        "account": {
            "account_id": account.account_id,
            "currency": account.currency,
            "balance": str(account.balance),
            "equity": str(account.equity),
        },
    }


@router.get("/practice/markets")
def practice_markets() -> list[dict]:
    state = runtime_store.state
    if state.broker == "mt5":
        if not runtime_store.broker_connected():
            raise HTTPException(status_code=503, detail="MT5 live prices are unavailable while the Windows worker is disconnected")
        instrument_map = {instrument.symbol: instrument for instrument in simulation_adapter.get_instruments()}
        instruments = []
        for quote in state.market_data:
            symbol = str(quote.get("base_symbol", "")).upper()
            instrument = instrument_map.get(symbol)
            if instrument is None:
                continue
            try:
                tick = get_live_mt5_tick(symbol)
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            if tick is None:
                raise HTTPException(status_code=503, detail=f"No MT5 live quote is available for {symbol}")
            instruments.append({
                "symbol": symbol,
                "description": quote.get("description", instrument.description),
                "bid": str(tick.bid),
                "ask": str(tick.ask),
                "spread": str(tick.ask - tick.bid),
                "time": tick.time.isoformat(),
                "digits": int(quote.get("digits", instrument.digits)),
                "contract_size": str(quote.get("contract_size", instrument.contract_size)),
                "tick_size": str(quote.get("tick_size", instrument.tick_size)),
                "tick_value": str(quote.get("tick_value", instrument.tick_value)),
                "minimum_volume": str(quote.get("minimum_volume", instrument.minimum_volume)),
                "maximum_volume": str(quote.get("maximum_volume", instrument.maximum_volume)),
                "volume_step": str(quote.get("volume_step", instrument.volume_step)),
                "trade_allowed": bool(quote.get("trade_allowed", instrument.trade_allowed)),
                "simulated": False,
                "execution_mode": "paper_only",
            })
        if not instruments:
            raise HTTPException(status_code=503, detail="No MT5 live quotes are available for practice trading")
        return instruments

    instruments = []
    for instrument in simulation_adapter.get_instruments():
        tick = simulation_adapter.get_tick(instrument.symbol)
        instruments.append({
            "symbol": instrument.symbol,
            "description": instrument.description,
            "bid": str(tick.bid),
            "ask": str(tick.ask),
            "spread": str(tick.ask - tick.bid),
            "time": tick.time.isoformat(),
            "digits": instrument.digits,
            "contract_size": str(instrument.contract_size),
            "tick_size": str(instrument.tick_size),
            "tick_value": str(instrument.tick_value),
            "minimum_volume": str(instrument.minimum_volume),
            "maximum_volume": str(instrument.maximum_volume),
            "volume_step": str(instrument.volume_step),
            "trade_allowed": instrument.trade_allowed,
            "simulated": True,
            "execution_mode": "paper_only",
        })
    return instruments


@router.get("/practice/positions")
def practice_positions() -> dict:
    state_before_refresh = simulation_adapter.export_state()
    try:
        pending_orders = simulation_adapter.get_pending_orders()
        items = simulation_adapter.get_open_positions()
        account = simulation_adapter.get_account_info()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if simulation_adapter.export_state() != state_before_refresh:
        save_runtime_state()
    return {
        "items": items,
        "total": len(items),
        "pending_orders": pending_orders,
        "pending_total": len(pending_orders),
        "connected": True,
        "simulated": True,
        "trading_mode": "paper_only",
        "account": {
            "account_id": account.account_id,
            "currency": account.currency,
            "balance": str(account.balance),
            "equity": str(account.equity),
        },
    }


@router.post("/practice/account/deposit")
def deposit_practice_account(payload: PracticeDepositRequest) -> dict:
    try:
        simulation_adapter.add_funds(payload.amount)
        account = simulation_adapter.get_account_info()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    save_runtime_state()
    return {
        "deposited": str(payload.amount),
        "simulated": True,
        "trading_mode": "paper_only",
        "account": {
            "currency": account.currency,
            "balance": str(account.balance),
            "equity": str(account.equity),
        },
    }


@router.get("/practice/history")
def practice_history() -> dict:
    state_before_refresh = simulation_adapter.export_state()
    items = simulation_adapter.get_deal_history()
    if simulation_adapter.export_state() != state_before_refresh:
        save_runtime_state()
    return {
        "items": items,
        "total": len(items),
        "connected": True,
        "simulated": True,
        "trading_mode": "paper_only",
    }


@router.get("/positions")
def positions() -> dict:
    state = runtime_store.state
    connected = runtime_store.broker_connected()
    if not connected:
        return {
            "items": [],
            "total": 0,
            "connected": False,
            "broker": state.broker,
            "can_trade_simulation": False,
            "environment": state.environment,
            "simulated": state.broker == "simulation",
            "trading_mode": "paper_only",
        }
    if state.broker == "mt5":
        items = [dict(position) for position in state.open_positions]
        simulated = False
    else:
        state_before_refresh = simulation_adapter.export_state()
        items = simulation_adapter.get_open_positions()
        if simulation_adapter.export_state() != state_before_refresh:
            save_runtime_state()
        simulated = True
    return {
        "items": items,
        "total": len(items),
        "connected": True,
        "broker": state.broker,
        "can_trade_simulation": state.broker == "simulation",
        "environment": state.environment,
        "simulated": simulated,
        "trading_mode": "paper_only",
    }


@router.post("/orders")
@router.post("/practice/orders")
def create_simulation_order(payload: SimulationOrderRequest) -> dict:
    settings = get_settings()
    account = simulation_adapter.get_account_info()
    max_risk_amount = account.equity * Decimal("0.01")
    max_aggregate_risk_amount = account.equity * settings.max_aggregate_open_risk_percent / Decimal("100")
    try:
        order = simulation_adapter.submit_order(
            payload.symbol,
            payload.direction,
            payload.volume,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            order_type=payload.order_type,
            stop_price=payload.stop_price,
            idempotency_key=payload.idempotency_key,
            max_risk_amount=max_risk_amount,
            max_aggregate_risk_amount=max_aggregate_risk_amount,
            max_open_positions=settings.max_simultaneous_positions,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    position = None
    if order.broker_position_id is not None:
        position = next(
            (item for item in simulation_adapter.get_open_positions() if item["ticket"] == order.broker_position_id),
            None,
        )
    save_runtime_state()
    return {
        "accepted": order.accepted,
        "simulated": True,
        "trading_mode": "paper_only",
        "order_type": payload.order_type,
        "status": order.status,
        "message": order.message,
        "position": position,
        "pending_order": (
            {
                "ticket": order.broker_order_id,
                "symbol": payload.symbol.upper(),
                "order_type": payload.order_type,
                "direction": payload.direction,
                "volume": str(payload.volume),
                "stop_price": str(payload.stop_price),
                "stop_loss": str(payload.stop_loss) if payload.stop_loss is not None else "0",
                "take_profit": str(payload.take_profit) if payload.take_profit is not None else "0",
                "simulated": True,
            }
            if order.broker_position_id is None
            else None
        ),
    }


@router.delete("/practice/orders/{ticket}")
def cancel_practice_order(ticket: str) -> dict:
    try:
        order = simulation_adapter.cancel_pending_order(ticket)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    save_runtime_state()
    return {"cancelled": True, "simulated": True, "trading_mode": "paper_only", "order": order}


@router.post("/positions/{ticket}/close")
@router.post("/practice/positions/{ticket}/close")
def close_simulation_position(ticket: str) -> dict:
    try:
        deal = simulation_adapter.close_position(ticket)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    save_runtime_state()
    return {"closed": True, "simulated": True, "trading_mode": "paper_only", "deal": deal}


@router.post("/practice/positions/close-bulk")
def close_simulation_positions(payload: CloseSimulationPositionsRequest) -> dict:
    try:
        deals = simulation_adapter.close_positions(payload.tickets)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    save_runtime_state()
    return {
        "closed": len(deals),
        "simulated": True,
        "trading_mode": "paper_only",
        "deals": deals,
    }


@router.patch("/practice/positions/{ticket}")
def modify_simulation_position(ticket: str, payload: ModifySimulationPositionRequest) -> dict:
    settings = get_settings()
    try:
        account = simulation_adapter.get_account_info()
        position = simulation_adapter.modify_position(
            ticket,
            payload.stop_loss,
            payload.take_profit,
            max_risk_amount=account.equity * Decimal("0.01"),
            max_aggregate_risk_amount=(
                account.equity * settings.max_aggregate_open_risk_percent / Decimal("100")
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    save_runtime_state()
    return {
        "modified": True,
        "simulated": True,
        "trading_mode": "paper_only",
        "position": position,
    }


@router.get("/history")
def account_history(db: Session = Depends(get_db)) -> dict:
    state = runtime_store.state
    connected = runtime_store.broker_connected()
    items = []
    if connected and state.broker == "mt5":
        deals = db.scalars(
            select(TradeDeal)
            .where(
                TradeDeal.account_id == state.account_id,
                TradeDeal.server == state.server,
                TradeDeal.environment == state.environment,
                TradeDeal.deal_time >= datetime.now(UTC) - timedelta(days=30),
            )
            .order_by(TradeDeal.deal_time.desc())
            .limit(500)
        ).all()
        for deal in deals:
            deal_time = deal.deal_time
            if deal_time.tzinfo is None:
                deal_time = deal_time.replace(tzinfo=UTC)
            net_profit = deal.profit + deal.commission + deal.swap
            items.append({
                "ticket": deal.ticket,
                "order": deal.order_ticket,
                "symbol": deal.symbol,
                "direction": deal.direction,
                "volume": _format_decimal(deal.volume),
                "price": _format_decimal(deal.price),
                "profit": _format_decimal(deal.profit),
                "commission": _format_decimal(deal.commission),
                "swap": _format_decimal(deal.swap),
                "net_profit": _format_decimal(net_profit),
                "time": deal_time.isoformat(),
                "simulated": deal.simulated,
            })
    elif connected and state.broker == "simulation":
        state_before_refresh = simulation_adapter.export_state()
        items = simulation_adapter.get_deal_history()
        if simulation_adapter.export_state() != state_before_refresh:
            save_runtime_state()
    return {
        "items": items,
        "total": len(items),
        "connected": connected,
        "environment": state.environment,
        "currency": state.account_currency,
        "simulated": state.broker == "simulation",
        "period_days": 30,
        "trading_mode": "paper_only",
    }
