from collections.abc import Mapping, Sequence
from trading.analysis.indicators import calculate_indicators
from trading.analysis.market_structure import market_structure


def analyse_timeframes(candles_by_timeframe: Mapping[str, Sequence]) -> dict:
    weights = {"M5": 1, "M15": 2, "M30": 2, "H1": 3, "H4": 4, "D1": 5}
    bullish = 0
    bearish = 0
    results: dict[str, dict] = {}
    for timeframe, candles in candles_by_timeframe.items():
        if len(candles) < 2:
            continue
        indicators = calculate_indicators(candles)
        structure = market_structure(candles)
        direction = "bullish" if indicators.ema50 > indicators.ema200 else "bearish" if indicators.ema50 < indicators.ema200 else "neutral"
        results[timeframe] = {"structure": structure, "direction": direction}
        weight = weights.get(timeframe, 1)
        if direction == "bullish":
            bullish += weight
        elif direction == "bearish":
            bearish += weight
    if bullish == bearish:
        consensus = "neutral"
    elif bullish > bearish:
        consensus = "bullish"
    else:
        consensus = "bearish"
    return {"consensus": consensus, "timeframes": results}
