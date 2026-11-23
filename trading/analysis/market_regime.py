from collections.abc import Sequence
from shared.contracts.analysis import IndicatorSet


def classify_regime(indicators: IndicatorSet, candle_range: float) -> str:
    if indicators.adx >= 25 and abs(indicators.ema50 - indicators.ema200) / max(abs(indicators.ema200), 1e-9) > 0.0005:
        return "trending"
    if indicators.atr14 > candle_range:
        return "high_volatility"
    if indicators.atr14 < candle_range * 0.5:
        return "low_volatility"
    if indicators.adx < 20:
        return "ranging"
    return "uncertain"
