import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import AuthenticationMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.broker import router as broker_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.signals import router as signals_router
from app.api.v1.risk import router as risk_router
from app.api.v1.backtesting import router as backtesting_router
from app.api.v1.notifications import router as notifications_router
from app.core.config import get_settings
from app.core.runtime import runtime_store
from app.api.v1 import signals as signals_api
from app.core.persistent_runtime import restore_runtime_state


async def realtime_signal_scanner() -> None:
    while True:
        await asyncio.sleep(signals_api.realtime_state["interval_seconds"])
        if not runtime_store.broker_connected():
            continue
        try:
            for symbol in signals_api.REALTIME_SYMBOLS:
                await asyncio.to_thread(signals_api.generate_signals, symbol, "ALL")
            signals_api.realtime_state["last_scan_at"] = datetime.now(UTC).isoformat()
            signals_api.realtime_state["last_scan_error"] = None
        except Exception as exc:
            signals_api.realtime_state["last_scan_error"] = str(exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    restore_runtime_state()
    task = asyncio.create_task(realtime_signal_scanner())
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(broker_router, prefix=settings.api_v1_prefix)
app.include_router(analysis_router, prefix=settings.api_v1_prefix)
app.include_router(signals_router, prefix=settings.api_v1_prefix)
app.include_router(risk_router, prefix=settings.api_v1_prefix)
app.include_router(backtesting_router, prefix=settings.api_v1_prefix)
app.include_router(notifications_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def api_root() -> dict:
    return {
        "service": settings.app_name,
        "status": "running",
        "health": "/health",
        "documentation": "/docs",
        "dashboard": "http://localhost:3000/dashboard",
    }
