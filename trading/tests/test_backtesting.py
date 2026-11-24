from datetime import UTC, datetime, timedelta
from decimal import Decimal

from shared.contracts.broker import Candle
from trading.backtesting.engine import backtest_strategy
from trading.strategies.base import StrategySignal


class SingleBuySignal:
    def __init__(self) -> None:
        self.emitted = False

    def evaluate(self, symbol: str, timeframe: str, candles: list, context=None) -> StrategySignal | None:
        if self.emitted:
            return None
        self.emitted = True
        return StrategySignal(
            "single_test_signal", "BUY", timeframe, 100, 99, 100.5, 101, 102, 80, "test",
        )


class TwoTradeSignals:
    def evaluate(self, symbol: str, timeframe: str, candles: list, context=None) -> StrategySignal | None:
        if len(candles) == 2:
            return StrategySignal(
                "test_buy", "BUY", timeframe, 100, 99, 100.5, 101, 102, 80, "test",
            )
        if len(candles) == 4:
            return StrategySignal(
                "test_sell", "SELL", timeframe, 100, 101, 99.5, 99, 98, 80, "test",
            )
        return None


def candle(time: datetime, high: str, low: str, close: str = "100") -> Candle:
    return Candle("TEST", "M5", time, Decimal("100"), Decimal(high), Decimal(low), Decimal(close), Decimal("1"))


def test_backtest_assumes_stop_first_when_stop_and_target_hit_same_candle():
    now = datetime.now(UTC)
    candles = [
        candle(now, "100.5", "99.5"),
        candle(now + timedelta(minutes=5), "100.5", "99.5"),
        candle(now + timedelta(minutes=10), "102.5", "98.5"),
    ]

    result = backtest_strategy("TEST", "M5", candles, SingleBuySignal())

    trade = result["trades"][0]
    assert trade["outcome"] == "STOP_LOSS"
    assert trade["r_multiple"] == "-1"
    assert trade["ambiguous_exit"] is True
    assert result["summary"]["net_r"] == "-1"
    assert result["summary"]["max_drawdown_r"] == "1"


def test_backtest_records_take_profit_as_positive_reward_multiple():
    now = datetime.now(UTC)
    candles = [
        candle(now, "100.5", "99.5"),
        candle(now + timedelta(minutes=5), "100.5", "99.5"),
        candle(now + timedelta(minutes=10), "102.5", "99.5"),
        candle(now + timedelta(minutes=15), "101", "99.5"),
    ]

    result = backtest_strategy("TEST", "M5", candles, SingleBuySignal())

    assert result["trades"][0]["outcome"] == "TAKE_PROFIT"
    assert result["trades"][0]["r_multiple"] == "2"
    assert result["summary"]["wins"] == 1
    assert result["summary"]["open_trades"] == 0


def test_backtest_does_not_count_unresolved_trade_as_a_loss():
    now = datetime.now(UTC)
    candles = [
        candle(now, "100.5", "99.5"),
        candle(now + timedelta(minutes=5), "100.5", "99.5"),
        candle(now + timedelta(minutes=10), "101", "99.5"),
    ]

    result = backtest_strategy("TEST", "M5", candles, SingleBuySignal())

    assert result["trades"][0]["outcome"] == "OPEN"
    assert result["trades"][0]["r_multiple"] is None
    assert result["summary"]["open_trades"] == 1
    assert result["summary"]["resolved_trades"] == 0
    assert result["equity_curve"] == []


def test_backtest_equity_curve_tracks_cumulative_r_and_drawdown():
    now = datetime.now(UTC)
    candles = [
        candle(now, "100.5", "99.5"),
        candle(now + timedelta(minutes=5), "100.5", "99.5"),
        candle(now + timedelta(minutes=10), "102.5", "99.5"),
        candle(now + timedelta(minutes=15), "100.5", "99.5"),
        candle(now + timedelta(minutes=20), "101.5", "99.5"),
        candle(now + timedelta(minutes=25), "100.5", "99.5"),
    ]

    result = backtest_strategy("TEST", "M5", candles, TwoTradeSignals(), tick_size=Decimal("0.01"))

    assert [trade["outcome"] for trade in result["trades"]] == ["TAKE_PROFIT", "STOP_LOSS"]
    assert result["equity_curve"] == [
        {
            "trade_number": 1,
            "time": candles[2].time.isoformat(),
            "cumulative_r": "2",
            "drawdown_r": "0",
        },
        {
            "trade_number": 2,
            "time": candles[4].time.isoformat(),
            "cumulative_r": "1",
            "drawdown_r": "1",
        },
    ]
