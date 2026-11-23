from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.core.broker import simulation_adapter
from app.core.market_data import get_mt5_candles
from app.core.real_market_data import get_real_market_candles
from app.core.runtime import runtime_store
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
    end = datetime.now(UTC)
    multipliers = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
    candles_by_timeframe = {}
    missing_timeframes = []
    simulated = runtime_store.state.broker != "mt5"
    if not simulated:
        if not runtime_store.broker_connected():
            raise HTTPException(status_code=503, detail="MT5 worker is disconnected; refusing to substitute simulation candles")
        primary = get_mt5_candles(symbol.upper(), timeframe)
        if primary is None:
            raise HTTPException(status_code=503, detail=f"No MT5 {timeframe} candle history is available for {symbol.upper()}")
        actual_symbol, candles = primary
        for other_timeframe in multipliers:
            if other_timeframe == timeframe:
                continue
            snapshot = get_mt5_candles(symbol.upper(), other_timeframe)
            if snapshot is None:
                missing_timeframes.append(other_timeframe)
                continue
            completed_snapshot = snapshot[1][:-1]
            if len(completed_snapshot) < 2:
                missing_timeframes.append(other_timeframe)
                continue
            candles_by_timeframe[other_timeframe] = completed_snapshot
    else:
        actual_symbol = symbol.upper()
        start = end - timedelta(minutes=multipliers[timeframe] * 260)
        try:
            candles = get_real_market_candles(actual_symbol, timeframe)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        for other_timeframe, multiplier in multipliers.items():
            if other_timeframe == timeframe:
                continue
            other_start = end - timedelta(minutes=multiplier * 260)
            try:
                other_candles = get_real_market_candles(actual_symbol, other_timeframe)
            except (KeyError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            candles_by_timeframe[other_timeframe] = other_candles[:-1]

    completed = candles[:-1] if len(candles) > 1 else candles
    if len(completed) < 2:
        return {
            "symbol": actual_symbol,
            "timeframe": timeframe,
            "status": "insufficient_completed_candles",
            "simulated": simulated,
            "data_source": "simulation" if simulated else "mt5",
        }

    indicators = calculate_indicators(completed)
    range_value = max(float(candle.high - candle.low) for candle in completed[-20:])
    candles_by_timeframe[timeframe] = completed
    strategy_signals = [
        strategy.evaluate(actual_symbol, timeframe, completed)
        for strategy in (TrendFollowingStrategy(), BreakoutRetestStrategy())
    ]
    support, resistance = support_resistance(completed)
    return {
        "symbol": actual_symbol,
        "timeframe": timeframe,
        "completed_candles": len(completed),
        "trend": trend_direction(completed),
        "structure": market_structure(completed),
        "regime": classify_regime(indicators, range_value),
        "indicators": indicators.__dict__,
        "multi_timeframe": analyse_timeframes(candles_by_timeframe),
        "support_resistance": {
            "support": support,
            "resistance": resistance,
        },
        "strategy_signals": [
            signal.__dict__ for signal in strategy_signals if signal is not None
        ],
        "simulated": simulated,
        "data_source": "simulation" if simulated else "mt5",
        "missing_timeframes": missing_timeframes,
    }
