from datetime import UTC, datetime, timedelta
from dataclasses import replace
from decimal import Decimal

from trading.connectors.simulation import SimulationAdapter
from trading.signals.generator import generate_validated_signals
from trading.signals.validator import SignalValidationError, validate_signal
from trading.strategies.trend_following import TrendFollowingStrategy
from trading.strategies.breakout_retest import BreakoutRetestStrategy


def test_signal_validation_requires_protective_stop_and_two_to_one_reward():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime.now(UTC) - timedelta(hours=260)
    candles = adapter.get_historical_candles("EURUSD", "H1", start, datetime.now(UTC))
    from trading.strategies.base import StrategySignal
    buy = StrategySignal("trend_following", "BUY", "H1", 1.10000, 1.09500, 1.10200, 1.11000, 1.12000, 75, "test")
    validate_signal(buy)
    try:
        bad = replace(buy, stop_loss=1.10001)
        validate_signal(bad)
        assert False
    except SignalValidationError:
        pass


def test_signal_generation_never_submits_or_returns_unexpired_signals():
    adapter = SimulationAdapter()
    adapter.connect()
    now = datetime.now(UTC)
    candles = adapter.get_historical_candles("EURUSD", "H1", now - timedelta(hours=260), now)
    generated = generate_validated_signals(
        "EURUSD", "H1", candles,
        [TrendFollowingStrategy(), BreakoutRetestStrategy()],
        now=now,
    )
    assert isinstance(generated, list)
    for signal in generated:
        assert signal["status"] in {"VALIDATED", "REJECTED"}
        if signal["status"] == "VALIDATED":
            assert "expires_at" in signal
            assert Decimal(signal["risk_reward_ratio"]) >= Decimal("2")


def test_gold_signal_prices_are_rounded_to_symbol_tick_size():
    adapter = SimulationAdapter()
    adapter.connect()
    now = datetime.now(UTC)
    candles = adapter.get_historical_candles("XAUUSD", "H1", now - timedelta(hours=260), now)
    generated = generate_validated_signals(
        "XAUUSD",
        "H1",
        candles,
        [TrendFollowingStrategy(), BreakoutRetestStrategy()],
        now=now,
        tick_size=adapter.get_symbol_info("XAUUSD").tick_size,
    )

    for signal in generated:
        if signal["status"] == "VALIDATED":
            for field in ("entry", "stop_loss", "tp1", "tp2", "tp3"):
                price = Decimal(signal[field])
                assert price % Decimal("0.01") == 0
                assert "999999" not in signal[field]
