from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from shared.contracts.broker import Tick
from trading.connectors.simulation import SimulationAdapter


def test_simulation_connection_and_account():
    adapter = SimulationAdapter()
    assert adapter.connect()
    account = adapter.get_account_info()
    assert account.environment == "simulation"
    assert account.currency == "USD"
    assert account.balance == Decimal("10000")
    assert account.simulated


def test_simulation_account_can_add_funds():
    adapter = SimulationAdapter()
    adapter.connect()

    balance = adapter.add_funds(Decimal("250.50"))

    assert balance == Decimal("10250.50")
    assert adapter.get_account_info().balance == Decimal("10250.50")


def test_simulation_account_rejects_non_positive_funds():
    adapter = SimulationAdapter()
    adapter.connect()

    for amount in (Decimal("0"), Decimal("-1")):
        with pytest.raises(ValueError, match="positive finite"):
            adapter.add_funds(amount)

    assert adapter.get_account_info().balance == Decimal("10000")


def test_simulation_instruments_and_ticks():
    adapter = SimulationAdapter()
    adapter.connect()
    instruments = adapter.get_instruments()
    assert {item.symbol for item in instruments} == {
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
        "EURGBP", "EURJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
        "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
        "AUDJPY", "AUDCAD", "AUDNZD", "AUDCHF", "CADJPY", "CADCHF", "CHFJPY",
        "NZDJPY", "NZDCAD", "NZDCHF", "XAUUSD",
        "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD",
        "ADAUSD", "DOGEUSD", "LTCUSD", "BCHUSD", "AVAXUSD",
    }
    tick = adapter.get_tick("EURUSD")
    assert tick.ask >= tick.bid
    assert tick.symbol == "EURUSD"


def test_crypto_instrument_specs_and_quotes_use_crypto_reference_prices():
    adapter = SimulationAdapter()
    adapter.connect()

    for symbol in ("BTCUSD", "ETHUSD", "XRPUSD", "DOGEUSD"):
        info = adapter.get_symbol_info(symbol)
        tick = adapter.get_tick(symbol)

        assert info.contract_size == Decimal("1")
        assert info.tick_value == info.tick_size
        assert info.volume_step == Decimal("0.001")
        assert tick.ask > tick.bid
        assert abs(tick.bid - adapter.REFERENCE_PRICES[symbol]) <= info.tick_size * 49


def test_forex_cross_quote_uses_its_pair_reference_price():
    adapter = SimulationAdapter()
    adapter.connect()

    info = adapter.get_symbol_info("EURGBP")
    tick = adapter.get_tick("EURGBP")

    assert abs(tick.bid - adapter.REFERENCE_PRICES["EURGBP"]) <= info.tick_size * 49


def test_simulation_historical_candles_are_completed_range():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = adapter.get_historical_candles("EURUSD", "H1", start, start + timedelta(hours=2))
    assert len(candles) == 3
    assert all(candle.symbol == "EURUSD" for candle in candles)
    assert all(candle.high >= candle.low for candle in candles)


def test_simulation_historical_candles_support_one_minute():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, tzinfo=UTC)

    candles = adapter.get_historical_candles("EURUSD", "M1", start, start + timedelta(minutes=2))

    assert len(candles) == 3
    assert all(candle.timeframe == "M1" for candle in candles)


def test_simulation_historical_candles_include_bullish_and_bearish_bars():
    adapter = SimulationAdapter()
    adapter.connect()
    start = datetime(2026, 1, 1, 0, 45, tzinfo=UTC)

    candles = adapter.get_historical_candles("EURUSD", "H1", start, start + timedelta(hours=80))
    directions = {candle.close > candle.open for candle in candles}

    assert directions == {False, True}
    assert candles[0].time == datetime(2026, 1, 1, tzinfo=UTC)
    assert all(candle.time.minute == 0 for candle in candles)
    assert all(candle.low < min(candle.open, candle.close) for candle in candles)
    assert all(candle.high > max(candle.open, candle.close) for candle in candles)
    assert len({candle.volume for candle in candles}) > 1


def test_simulation_market_order_allows_optional_stops_and_is_idempotent():
    adapter = SimulationAdapter()
    adapter.connect()
    first = adapter.submit_order("EURUSD", "BUY", Decimal("0.01"), idempotency_key="test-key")
    second = adapter.submit_order("EURUSD", "BUY", Decimal("0.01"), idempotency_key="test-key")

    assert first.accepted
    assert first.simulated
    assert second.status == "IDEMPOTENT_RETURN"
    assert second.broker_order_id == first.broker_order_id
    position = adapter.get_open_positions()[0]
    assert position["stop_loss"] == "0"
    assert position["take_profit"] == "0"


def test_simulation_buy_stop_triggers_at_entry_price_and_can_be_cancelled():
    adapter = SimulationAdapter()
    adapter.connect()
    tick = Tick("EURUSD", Decimal("1.10000"), Decimal("1.10010"), datetime.now(UTC))
    adapter.get_tick = lambda _symbol: tick

    pending = adapter.submit_order(
        "EURUSD",
        "BUY",
        Decimal("0.01"),
        order_type="BUY_STOP",
        stop_price=Decimal("1.10100"),
    )
    assert pending.status == "placed"
    assert adapter.get_pending_orders()[0]["order_type"] == "BUY_STOP"

    tick = Tick("EURUSD", Decimal("1.10100"), Decimal("1.10110"), datetime.now(UTC))
    assert adapter.get_pending_orders() == []
    position = adapter.get_open_positions()[0]
    assert position["direction"] == "BUY"
    assert position["price_open"] == "1.10100"
    assert adapter.get_deal_history()[0]["deal_type"] == "ENTRY"

    cancelled = adapter.submit_order(
        "EURUSD",
        "SELL",
        Decimal("0.01"),
        order_type="SELL_STOP",
        stop_price=Decimal("1.09900"),
    )
    assert adapter.cancel_pending_order(cancelled.broker_order_id)["status"] == "cancelled"
    assert adapter.get_pending_orders() == []


def test_simulation_sell_stop_triggers_below_market():
    adapter = SimulationAdapter()
    adapter.connect()
    tick = Tick("EURUSD", Decimal("1.10000"), Decimal("1.10010"), datetime.now(UTC))
    adapter.get_tick = lambda _symbol: tick
    adapter.submit_order(
        "EURUSD",
        "SELL",
        Decimal("0.01"),
        order_type="SELL_STOP",
        stop_price=Decimal("1.09900"),
    )

    tick = Tick("EURUSD", Decimal("1.09890"), Decimal("1.09900"), datetime.now(UTC))
    assert adapter.get_pending_orders() == []
    position = adapter.get_open_positions()[0]
    assert position["direction"] == "SELL"
    assert position["price_open"] == "1.09900"
