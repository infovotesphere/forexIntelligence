from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.core.runtime import runtime_store

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception:
        database_status = "unhealthy"

    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        redis.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    state = runtime_store.state
    broker_status = "connected" if runtime_store.broker_connected() else "disconnected"
    worker_status = (
        "connected"
        if state.broker == "mt5" and state.mt5_connected and runtime_store.broker_connected()
        else "not_connected"
    )
    status = "ok" if database_status == "healthy" and redis_status == "healthy" else "degraded"

    return {
        "status": status,
        "database": database_status,
        "redis": redis_status,
        "broker": broker_status,
        "broker_type": state.broker,
        "mt5_worker": worker_status,
        "engine_running": state.engine_running,
        "live_trading": settings.live_trading_enabled,
        "environment": settings.environment,
    }
