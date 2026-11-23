from collections.abc import Mapping, Sequence

from trading.analysis.indicators import calculate_indicators
from trading.strategies.base import Strategy, StrategySignal


class BreakoutRetestStrategy(Strategy):
    name = "breakout_retest"

    def evaluate(self, symbol: str, timeframe: str, candles: Sequence, context: Mapping | None = None) -> StrategySignal | None:
        if len(candles) < 30:
            return None
        range_candles = candles[-30:-3]
        resistance = max(float(candle.high) for candle in range_candles)
        support = min(float(candle.low) for candle in range_candles)
        breakout = candles[-3:]
        indicators = calculate_indicators(candles)
        close = float(candles[-1].close)

        if float(breakout[-2].close) > resistance and float(candles[-1].close) <= resistance * 1.0005 and close >= resistance:
            stop = close - 1.5 * indicators.atr14
            return StrategySignal(self.name, "BUY", timeframe, close, stop, close + 1.5 * indicators.atr14, close + 3 * indicators.atr14, close + 4.5 * indicators.atr14, 70, "Bullish range breakout followed by retest")
        if float(breakout[-2].close) < support and float(candles[-1].close) >= support * 0.9995 and close <= support:
            stop = close + 1.5 * indicators.atr14
            return StrategySignal(self.name, "SELL", timeframe, close, stop, close - 1.5 * indicators.atr14, close - 3 * indicators.atr14, close - 4.5 * indicators.atr14, 70, "Bearish range breakout followed by retest")
        return None
