from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, HTTPException, Query

from app.core.broker import simulation_adapter
from app.core.market_data import get_mt5_candles
from app.core.runtime import runtime_store
from trading.signals.generator import generate_validated_signals
from trading.strategies.trend_following import TrendFollowingStrategy
from trading.strategies.breakout_retest import BreakoutRetestStrategy

router = APIRouter(prefix="/signals", tags=["signals"])
signal_store: list[dict] = []


@router.get("/")
@router.get("")
def list_signals(status: str | None = None) -> dict:
    now = datetime.now(UTC)
    items = []
    for signal in signal_store:
        item = dict(signal)
        if item["status"] == "VALIDATED" and item.get("expires_at"):
            expires_at = datetime.fromisoformat(item["expires_at"])
            if expires_at <= now:
                item["status"] = "EXPIRED"
        if status is None or item["status"] == status.upper():
            items.append(item)
    return {"items": items, "total": len(items), "page": 1, "page_size": 100}


@router.post("/generate")
def generate_signals(
    symbol: str = Query(min_length=1),
    timeframe: str = Query(default="H1", pattern="^(M5|M15|M30|H1|H4|D1)$"),
) -> dict:
    simulated = runtime_store.state.broker != "mt5"
    try:
        if not simulated:
            if not runtime_store.broker_connected():
                raise HTTPException(status_code=503, detail="MT5 worker is disconnected; refusing to substitute simulation candles")
            snapshot = get_mt5_candles(symbol.upper(), timeframe)
            if snapshot is None:
                raise HTTPException(status_code=503, detail=f"No MT5 {timeframe} candle history is available for {symbol.upper()}")
            actual_symbol, candles = snapshot
            quote = next(
                (
                    item for item in runtime_store.state.market_data
                    if str(item.get("base_symbol") or "").upper() == symbol.upper()
                    or str(item.get("symbol") or "").upper() == actual_symbol.upper()
                ),
                None,
            )
            if quote is None:
                raise HTTPException(status_code=503, detail=f"No MT5 quote metadata is available for {actual_symbol}")
            try:
                tick_size = Decimal(str(quote["tick_size"]))
            except (KeyError, InvalidOperation) as exc:
                raise HTTPException(status_code=503, detail=f"MT5 tick size is unavailable for {actual_symbol}") from exc
            if tick_size <= 0:
                raise HTTPException(status_code=503, detail=f"MT5 tick size is invalid for {actual_symbol}")
        else:
            end = datetime.now(UTC)
            minutes = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}[timeframe]
            candles = simulation_adapter.get_historical_candles(
                symbol.upper(), timeframe, end - timedelta(minutes=minutes * 260), end
            )
            actual_symbol = symbol.upper()
            tick_size = simulation_adapter.get_symbol_info(actual_symbol).tick_size
    except HTTPException:
        raise
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    generated = generate_validated_signals(
        actual_symbol, timeframe, candles,
        [TrendFollowingStrategy(), BreakoutRetestStrategy()],
        tick_size=tick_size,
    )
    for signal in generated:
        signal["simulated"] = simulated
        signal["data_source"] = "simulation" if simulated else "mt5"
    signal_store.extend(generated)
    if len(signal_store) > 1000:
        del signal_store[:-1000]
    return {
        "items": generated,
        "total": len(generated),
        "simulated": simulated,
        "data_source": "simulation" if simulated else "mt5",
    }
