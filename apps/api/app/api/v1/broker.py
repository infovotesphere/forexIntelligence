import hmac
import json
from decimal import Decimal
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Response, status
from pydantic import BaseModel, Field, SecretStr
from app.core.broker import simulation_adapter
from app.core.credential_encryption import CredentialEncryptionError, decrypt_credentials, encrypt_credentials
from app.core.config import get_settings
from app.core.runtime import runtime_store

router = APIRouter(tags=["broker"])


class DemoConnectRequest(BaseModel):
    broker: str = Field(default="simulation", pattern="^(simulation|mt5)$")
    environment: str = Field(default="demo", pattern="^(demo|live)$")
    live_read_only_confirmed: bool = False
    account_id: str | None = Field(default=None, pattern="^[0-9]{1,20}$")
    password: SecretStr | None = Field(default=None, max_length=255, repr=False)
    server: str | None = Field(default=None, max_length=255)


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
    open_positions: list[WorkerOpenPosition] = Field(default_factory=list, max_length=500)
    history_deals: list[WorkerDealSnapshot] = Field(default_factory=list, max_length=500)


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


@router.post("/worker/mt5/status")
def update_mt5_status(
    payload: WorkerStatusUpdate,
    authorization: str | None = Header(default=None),
) -> dict:
    require_worker(authorization)
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
    return {"running": state.engine_running, "broker_connected": runtime_store.broker_connected(),
            "environment": state.environment, "live_trading_enabled": False,
            "message": state.message}


@router.post("/engine/stop")
def stop_engine() -> dict:
    state = runtime_store.stop_engine()
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


@router.get("/positions")
def positions() -> dict:
    state = runtime_store.state
    connected = runtime_store.broker_connected()
    if not connected:
        return {
            "items": [],
            "total": 0,
            "connected": False,
            "environment": state.environment,
            "simulated": state.broker == "simulation",
            "trading_mode": "paper_only",
        }
    if state.broker == "mt5":
        items = [dict(position) for position in state.open_positions]
        simulated = False
    else:
        items = simulation_adapter.get_open_positions()
        simulated = True
    return {
        "items": items,
        "total": len(items),
        "connected": True,
        "environment": state.environment,
        "simulated": simulated,
        "trading_mode": "paper_only",
    }


@router.get("/history")
def account_history() -> dict:
    state = runtime_store.state
    connected = runtime_store.broker_connected()
    items = []
    if connected and state.broker == "mt5":
        for deal in state.history_deals[-500:]:
            item = dict(deal)
            item["net_profit"] = str(
                Decimal(str(item["profit"]))
                + Decimal(str(item["commission"]))
                + Decimal(str(item["swap"]))
            )
            items.append(item)
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
