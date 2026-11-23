from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading.connectors.simulation import SimulationAdapter


def test_simulation_connection_and_account():
    adapter = SimulationAdapter()
    assert adapter.connect()
    account = adapter.get_account_info()
    assert account.environment == "simulation"
    assert account.currency == "USD"
    assert account.balance == Decimal("10000")
    assert account.simulated


def test_simulation_instruments_and_ticks():
    adapter = SimulationAdapter()
    adapter.connect()
    instruments = adapter.get_instruments()
    assert {item.symbol for item in instruments} == {
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD"
    }
    tick = adapter.get_tick("EURUSD")
    assert tick.ask >= tick.bid
    assert tick.symbol == "EURUSD"


def test_simulation_historical_candles_are_completed_range():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = adapter.get_historical_candles("EURUSD", "H1", start, start + timedelta(hours=2))
    assert len(candles) == 3
    assert all(candle.symbol == "EURUSD" for candle in candles)
    assert all(candle.high >= candle.low for candle in candles)


def test_simulation_requires_stop_loss_and_is_idempotent():
    adapter = SimulationAdapter()
    adapter.connect()
    try:
        adapter.submit_order("EURUSD", "BUY", Decimal("0.01"))
        assert False, "Unprotected order should be rejected"
    except ValueError:
        pass

    first = adapter.submit_order("EURUSD", "BUY", Decimal("0.01"), stop_loss=Decimal("1.09000"), idempotency_key="test-key")
    second = adapter.submit_order("EURUSD", "BUY", Decimal("0.01"), stop_loss=Decimal("1.09000"), idempotency_key="test-key")
    assert first.accepted
    assert first.simulated
    assert second.status == "IDEMPOTENT_RETURN"
    assert second.broker_order_id == first.broker_order_id
