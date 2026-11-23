from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.core.broker import simulation_adapter
from trading.analysis.indicators import calculate_indicators
from trading.analysis.market_regime import classify_regime
from trading.analysis.market_structure import market_structure
from trading.analysis.multi_timeframe import analyse_timeframes
from trading.analysis.support_resistance import support_resistance
from trading.analysis.trend_analysis import trend_direction
from trading.strategies.trend_following import TrendFollowingStrategy
from trading.strategies.breakout_retest import BreakoutRetestStrategy

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{symbol}")
def analyse_symbol(
    symbol: str,
    timeframe: str = Query(default="H1", pattern="^(M5|M15|M30|H1|H4|D1)$"),
) -> dict:
    try:
        end = datetime.now(UTC)
        multipliers = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
        start = end - timedelta(minutes=multipliers[timeframe] * 260)
        candles = simulation_adapter.get_historical_candles(symbol.upper(), timeframe, start, end)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    completed = candles[:-1] if len(candles) > 1 else candles
    if len(completed) < 2:
        return {"symbol": symbol.upper(), "timeframe": timeframe, "status": "insufficient_completed_candles"}

    indicators = calculate_indicators(completed)
    range_value = max(float(candle.high - candle.low) for candle in completed[-20:])
    strategy_signals = [
        strategy.evaluate(symbol.upper(), timeframe, completed)
        for strategy in (TrendFollowingStrategy(), BreakoutRetestStrategy())
    ]
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "completed_candles": len(completed),
        "trend": trend_direction(completed),
        "structure": market_structure(completed),
        "regime": classify_regime(indicators, range_value),
        "indicators": indicators.__dict__,
        "support_resistance": {
            "support": support_resistance(completed)[0],
            "resistance": support_resistance(completed)[1],
        },
        "strategy_signals": [
            signal.__dict__ for signal in strategy_signals if signal is not None
        ],
        "simulated": True,
    }
