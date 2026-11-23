from datetime import UTC, datetime, timedelta
from trading.connectors.simulation import SimulationAdapter
from trading.analysis.indicators import calculate_indicators, ema, rsi
from trading.analysis.market_structure import market_structure
from trading.analysis.market_regime import classify_regime
from trading.analysis.multi_timeframe import analyse_timeframes


def test_indicator_calculations_are_deterministic_and_finite():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = adapter.get_historical_candles("EURUSD", "H1", start, start + timedelta(hours=250))
    indicators = calculate_indicators(candles)
    assert 0 <= indicators.rsi14 <= 100
    assert indicators.atr14 >= 0
    assert indicators.bollinger_upper >= indicators.bollinger_lower
    assert ema([1, 2, 3], 3)[-1] > 1
    assert len(rsi([1, 2, 3], 14)) == 3


def test_market_structure_and_regime():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = adapter.get_historical_candles("EURUSD", "H1", start, start + timedelta(hours=250))
    indicators = calculate_indicators(candles)
    structure = market_structure(candles)
    regime = classify_regime(indicators, 0.001)
    assert structure in {"higher_highs_higher_lows", "lower_highs_lower_lows", "break_of_structure_bullish", "break_of_structure_bearish", "range", "uncertain"}
    assert regime in {"trending", "ranging", "high_volatility", "low_volatility", "uncertain"}


def test_multi_timeframe_analysis():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = {timeframe: adapter.get_historical_candles("EURUSD", timeframe, start, start + timedelta(hours=250)) for timeframe in ("H1", "H4")}
    result = analyse_timeframes(candles)
    assert result["consensus"] in {"bullish", "bearish", "neutral"}
    assert set(result["timeframes"]) == {"H1", "H4"}
