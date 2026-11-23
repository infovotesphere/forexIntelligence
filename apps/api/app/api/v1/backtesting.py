from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.broker import simulation_adapter
from app.core.market_data import get_mt5_candles
from app.core.real_market_data import get_real_market_candles
from app.core.runtime import runtime_store
from trading.backtesting.engine import backtest_strategy
from trading.strategies.base import Strategy
from trading.strategies.breakout_retest import BreakoutRetestStrategy
from trading.strategies.trend_following import TrendFollowingStrategy

router = APIRouter(prefix="/backtesting", tags=["backtesting"])
STRATEGIES: dict[str, type[Strategy]] = {
    TrendFollowingStrategy.name: TrendFollowingStrategy,
    BreakoutRetestStrategy.name: BreakoutRetestStrategy,
}
TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


class BacktestRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    timeframe: Literal["M5", "M15", "M30", "H1", "H4", "D1"] = "H1"
    strategy: Literal["trend_following", "breakout_retest"] = "trend_following"
    bars: int = Field(default=260, ge=30, le=500)


@router.post("/run")
def run_backtest(payload: BacktestRequest) -> dict:
    end = datetime.now(UTC)
    timeframe_minutes = TIMEFRAME_MINUTES[payload.timeframe]
    state = runtime_store.state
    if state.broker == "mt5":
        if not runtime_store.broker_connected():
            raise HTTPException(
                status_code=503,
                detail="MT5 worker is disconnected; refusing to substitute simulation candles",
            )
        snapshot = get_mt5_candles(payload.symbol.upper(), payload.timeframe)
        if snapshot is None:
            raise HTTPException(
                status_code=503,
                detail=f"No MT5 {payload.timeframe} candle history is available for {payload.symbol.upper()}",
            )
        actual_symbol, broker_candles = snapshot
        quote = next(
            (
                item for item in state.market_data
                if str(item.get("base_symbol", "")).upper() == payload.symbol.upper()
                or str(item.get("symbol", "")).upper() == actual_symbol.upper()
            ),
            None,
        )
        if quote is None:
            raise HTTPException(
                status_code=503,
                detail=f"MT5 tick-size metadata is unavailable for {payload.symbol.upper()}",
            )
        try:
            tick_size = Decimal(str(quote["tick_size"]))
        except (KeyError, InvalidOperation) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"MT5 tick-size metadata is unavailable for {payload.symbol.upper()}",
            ) from exc
        if not tick_size.is_finite() or tick_size <= 0:
            raise HTTPException(
                status_code=503,
                detail=f"MT5 tick-size metadata is invalid for {payload.symbol.upper()}",
            )
        candles = broker_candles[-(payload.bars + 1):]
        if candles and candles[-1].time + timedelta(minutes=timeframe_minutes) > end:
            candles = candles[:-1]
        completed = candles[-payload.bars:]
        backtest_symbol = actual_symbol
        simulated = False
    elif state.broker == "simulation":
        try:
            candles = get_real_market_candles(payload.symbol.upper(), payload.timeframe)
            instrument = simulation_adapter.get_symbol_info(payload.symbol.upper())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        completed = candles[-(payload.bars + 1):-1]
        backtest_symbol = payload.symbol.upper()
        tick_size = instrument.tick_size
        simulated = True
    else:
        raise HTTPException(
            status_code=503,
            detail="No broker account is selected; connect MT5 for broker candles or explicitly connect simulation",
        )

    if len(completed) < 30:
        raise HTTPException(status_code=503, detail="At least 30 completed candles are required for a backtest")

    result = backtest_strategy(
        backtest_symbol,
        payload.timeframe,
        completed,
        STRATEGIES[payload.strategy](),
        tick_size=tick_size,
    )
    return {
        "symbol": backtest_symbol,
        "timeframe": payload.timeframe,
        "strategy": payload.strategy,
        "bars_tested": len(completed),
        "tick_size": str(tick_size),
        "simulated": simulated,
        "data_source": "simulation" if simulated else "mt5",
        "candles": [
            {
                "time": candle.time.isoformat(),
                "open": str(candle.open),
                "high": str(candle.high),
                "low": str(candle.low),
                "close": str(candle.close),
                "volume": str(candle.volume),
            }
            for candle in completed
        ],
        "execution_model": (
            f"Price source: {'real external market history' if simulated else 'read-only MT5 broker history'}. "
            "This is a paper replay; no broker orders are sent. Entry at signal candle close; exit at TP3 or stop loss. "
            "Stop loss is assumed first if both levels are touched in one candle. "
            "Spread, slippage, commissions and partial targets are not modeled."
        ),
        **result,
    }
