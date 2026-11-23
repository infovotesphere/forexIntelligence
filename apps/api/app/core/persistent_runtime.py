import json
from decimal import Decimal

from redis import Redis

from app.core.config import get_settings
from app.core.runtime import RuntimeState, runtime_store


RUNTIME_KEY = "forex-intelligence:runtime-state"


def save_runtime_state() -> None:
    settings = get_settings()
    state = runtime_store.state
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        redis.set(RUNTIME_KEY, json.dumps({
            "broker": state.broker,
            "environment": state.environment,
            "account_id": state.account_id,
            "server": state.server,
            "mt5_connected": state.mt5_connected,
            "engine_running": state.engine_running,
            "account_currency": state.account_currency,
            "balance": str(state.balance) if state.balance is not None else "",
            "equity": str(state.equity) if state.equity is not None else "",
            "message": state.message,
        }), ex=60 * 60 * 24)
    except Exception:
        return


def restore_runtime_state() -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        raw_payload = redis.get(RUNTIME_KEY)
        payload = json.loads(raw_payload) if raw_payload else None
    except Exception:
        return
    if not payload:
        return

    if not isinstance(payload, dict):
        return

    broker = str(payload.get("broker") or "none")
    if broker not in {"none", "simulation", "mt5"}:
        return

    balance = Decimal(payload["balance"]) if payload.get("balance") else None
    equity = Decimal(payload["equity"]) if payload.get("equity") else None
    engine_running = bool(payload.get("engine_running"))

    if broker == "simulation":
        state = RuntimeState(
            broker="simulation",
            environment="demo",
            account_id="SIM-DEMO-001",
            server="Simulation",
            mt5_connected=True,
            engine_running=engine_running,
            account_currency="USD",
            balance=balance or Decimal("10000"),
            equity=equity or Decimal("10000"),
            message=str(payload.get("message") or "Simulation demo account connected"),
        )
    elif broker == "mt5":
        state = RuntimeState(
            broker="mt5",
            environment=str(payload.get("environment") or "demo"),
            account_id=str(payload.get("account_id") or ""),
            server=str(payload.get("server") or ""),
            mt5_connected=False,
            engine_running=False,
            account_currency=str(payload.get("account_currency") or ""),
            balance=balance,
            equity=equity,
            message="MT5 account restored; waiting for the Windows worker heartbeat",
        )
    else:
        state = RuntimeState()

    runtime_store.state = state
