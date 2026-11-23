from collections.abc import Sequence


def market_structure(candles: Sequence, lookback: int = 5) -> str:
    if len(candles) < lookback * 2:
        return "uncertain"
    recent = candles[-lookback:]
    prior = candles[-lookback * 2:-lookback]
    recent_high = max(float(candle.high) for candle in recent)
    recent_low = min(float(candle.low) for candle in recent)
    prior_high = max(float(candle.high) for candle in prior)
    prior_low = min(float(candle.low) for candle in prior)
    if recent_high > prior_high and recent_low > prior_low:
        return "higher_highs_higher_lows"
    if recent_high < prior_high and recent_low < prior_low:
        return "lower_highs_lower_lows"
    if recent_high > prior_high:
        return "break_of_structure_bullish"
    if recent_low < prior_low:
        return "break_of_structure_bearish"
    return "range"
