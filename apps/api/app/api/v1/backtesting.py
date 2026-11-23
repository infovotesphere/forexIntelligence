from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.broker import simulation_adapter
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
    start = end - timedelta(minutes=TIMEFRAME_MINUTES[payload.timeframe] * payload.bars)
    try:
        candles = simulation_adapter.get_historical_candles(
            payload.symbol.upper(), payload.timeframe, start, end
        )
        instrument = simulation_adapter.get_symbol_info(payload.symbol.upper())
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    completed = candles[:-1]
    result = backtest_strategy(
        payload.symbol.upper(),
        payload.timeframe,
        completed,
        STRATEGIES[payload.strategy](),
        tick_size=instrument.tick_size,
    )
    return {
        "symbol": payload.symbol.upper(),
        "timeframe": payload.timeframe,
        "strategy": payload.strategy,
        "bars_tested": len(completed),
        "tick_size": str(instrument.tick_size),
        "simulated": True,
        "execution_model": (
            "Entry at signal candle close; exit at TP3 or stop loss. "
            "Stop loss is assumed first if both levels are touched in one candle. "
            "Spread, slippage, commissions and partial targets are not modeled."
        ),
        **result,
    }
