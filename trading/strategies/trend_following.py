from collections.abc import Mapping, Sequence

from trading.analysis.indicators import calculate_indicators
from trading.analysis.market_structure import market_structure
from trading.strategies.base import Strategy, StrategySignal


class TrendFollowingStrategy(Strategy):
    name = "trend_following"

    def evaluate(self, symbol: str, timeframe: str, candles: Sequence, context: Mapping | None = None) -> StrategySignal | None:
        if len(candles) < 200:
            return None
        indicators = calculate_indicators(candles)
        structure = market_structure(candles)
        close = float(candles[-1].close)
        atr = indicators.atr14
        if not atr > 0:
            return None

        if indicators.ema50 > indicators.ema200 and indicators.rsi14 >= 52 and indicators.macd > indicators.macd_signal:
            if structure not in {"higher_highs_higher_lows", "break_of_structure_bullish"}:
                return None
            stop = close - 1.5 * atr
            return StrategySignal(self.name, "BUY", timeframe, close, stop, close + 1.5 * atr, close + 3.0 * atr, close + 4.5 * atr, 75, "Confirmed bullish higher timeframe structure with momentum")

        if indicators.ema50 < indicators.ema200 and indicators.rsi14 <= 48 and indicators.macd < indicators.macd_signal:
            if structure not in {"lower_highs_lower_lows", "break_of_structure_bearish"}:
                return None
            stop = close + 1.5 * atr
            return StrategySignal(self.name, "SELL", timeframe, close, stop, close - 1.5 * atr, close - 3.0 * atr, close - 4.5 * atr, 75, "Confirmed bearish lower timeframe structure with momentum")
        return None
