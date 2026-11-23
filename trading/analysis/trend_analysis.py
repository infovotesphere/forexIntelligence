from collections.abc import Sequence
from trading.analysis.indicators import calculate_indicators


def trend_direction(candles: Sequence) -> str:
    if len(candles) < 2:
        return "uncertain"
    indicators = calculate_indicators(candles)
    if indicators.ema20 > indicators.ema50 > indicators.ema200:
        return "bullish"
    if indicators.ema20 < indicators.ema50 < indicators.ema200:
        return "bearish"
    return "uncertain"
