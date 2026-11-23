from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException, Query

from app.core.broker import simulation_adapter
from trading.signals.generator import generate_validated_signals
from trading.strategies.trend_following import TrendFollowingStrategy
from trading.strategies.breakout_retest import BreakoutRetestStrategy

router = APIRouter(prefix="/signals", tags=["signals"])
signal_store: list[dict] = []


@router.get("/")
def list_signals(status: str | None = None) -> dict:
    items = signal_store
    if status:
        items = [signal for signal in items if signal["status"] == status.upper()]
    return {"items": items, "total": len(items), "page": 1, "page_size": 100}


@router.post("/generate")
def generate_signals(
    symbol: str = Query(min_length=1),
    timeframe: str = Query(default="H1", pattern="^(M5|M15|M30|H1|H4|D1)$"),
) -> dict:
    try:
        end = datetime.now(UTC)
        minutes = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}[timeframe]
        from datetime import timedelta
        candles = simulation_adapter.get_historical_candles(
            symbol.upper(), timeframe, end - timedelta(minutes=minutes * 260), end
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    generated = generate_validated_signals(
        symbol.upper(), timeframe, candles,
        [TrendFollowingStrategy(), BreakoutRetestStrategy()],
    )
    signal_store.extend(generated)
    if len(signal_store) > 1000:
        del signal_store[:-1000]
    return {"items": generated, "total": len(generated), "simulated": True}
