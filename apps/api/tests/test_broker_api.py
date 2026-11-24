from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from shared.contracts.broker import Candle, Tick
from app.api.v1 import broker as broker_api
import app.core.broker as broker_core
import app.core.persistent_runtime as persistent_runtime
from app.core.auth import AUTH_COOKIE_NAME
from app.core.broker import simulation_adapter
from app.main import app
from app.core.security import create_access_token
from app.core.runtime import RuntimeState, runtime_store

client = TestClient(app, cookies={AUTH_COOKIE_NAME: create_access_token("test@example.com", "administrator")})


def test_account_status_is_simulation():
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    response = client.get("/api/v1/accounts/status")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["environment"] == "demo"
    assert body["broker"] == "simulation"
    assert body["simulated"] is True


def test_account_and_market_endpoints():
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    account = client.get("/api/v1/accounts")
    assert account.status_code == 200
    assert account.json()["simulated"] is True

    markets = client.get("/api/v1/markets")
    assert markets.status_code == 200
    instruments = markets.json()
    symbols = {instrument["symbol"] for instrument in instruments}
    assert {"EURUSD", "GBPUSD", "EURGBP", "XAUUSD", "BTCUSD", "ETHUSD"} <= symbols
    eurusd = next(instrument for instrument in instruments if instrument["symbol"] == "EURUSD")
    assert Decimal(eurusd["ask"]) > Decimal(eurusd["bid"])
    assert Decimal(eurusd["spread"]) == Decimal(eurusd["ask"]) - Decimal(eurusd["bid"])
    assert eurusd["simulated"] is True


def test_simulation_chart_uses_real_market_ohlc(monkeypatch):
    now = datetime.now(UTC)
    candle = Candle(
        symbol="EURUSD",
        timeframe="M5",
        time=now,
        open=Decimal("1.09000"),
        high=Decimal("1.09100"),
        low=Decimal("1.08900"),
        close=Decimal("1.09050"),
        volume=Decimal("100"),
    )
    monkeypatch.setattr(runtime_store, "state", RuntimeState(broker="simulation", mt5_connected=True))
    monkeypatch.setattr(broker_core, "_simulation_market_ticks", {})
    monkeypatch.setattr(broker_api, "get_real_market_candles", lambda *_args, **_kwargs: [candle])

    response = client.get("/api/v1/markets/EURUSD/candles?timeframe=M5&limit=30")

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["data_source"] == "real_market"
    assert body["simulated"] is True
    assert body["candles"][-1]["close"] == "1.09050"


def test_real_market_chart_quote_is_used_to_open_and_protect_simulated_positions(monkeypatch):
    now = datetime.now(UTC)
    candle = Candle(
        symbol="EURUSD",
        timeframe="M5",
        time=now,
        open=Decimal("1.09000"),
        high=Decimal("1.09100"),
        low=Decimal("1.08900"),
        close=Decimal("1.09050"),
        volume=Decimal("100"),
    )
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    monkeypatch.setattr(runtime_store, "state", RuntimeState(broker="simulation"))
    monkeypatch.setattr(broker_core, "_simulation_market_ticks", {})
    monkeypatch.setattr(broker_api, "get_real_market_candles", lambda *_args, **_kwargs: [candle])
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: None)

    try:
        candles = client.get("/api/v1/markets/EURUSD/candles?timeframe=M5&limit=30")
        tick = simulation_adapter.get_tick("EURUSD")
        opened = client.post(
            "/api/v1/practice/orders",
            json={"symbol": "EURUSD", "direction": "BUY", "volume": "0.01"},
        )
        assert candles.status_code == 200
        assert tick.bid == Decimal("1.09045")
        assert tick.ask == Decimal("1.09055")
        assert opened.status_code == 200
        assert opened.json()["position"]["price_open"] == "1.09055"

        modified = client.patch(
            f"/api/v1/practice/positions/{opened.json()['position']['ticket']}",
            json={"stop_loss": "1.09000", "take_profit": "1.09100"},
        )

        assert modified.status_code == 200
        assert modified.json()["position"]["stop_loss"] == "1.09000"
        assert modified.json()["position"]["take_profit"] == "1.09100"
    finally:
        simulation_adapter.restore_state(previous_book)


def test_sell_position_accepts_protection_on_the_correct_side_of_the_current_ask(monkeypatch):
    now = datetime.now(UTC)
    candle = Candle(
        symbol="XAUUSD",
        timeframe="M5",
        time=now,
        open=Decimal("3622.30"),
        high=Decimal("3622.80"),
        low=Decimal("3622.10"),
        close=Decimal("3622.50"),
        volume=Decimal("100"),
    )
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    monkeypatch.setattr(runtime_store, "state", RuntimeState(broker="simulation"))
    monkeypatch.setattr(broker_core, "_simulation_market_ticks", {})
    monkeypatch.setattr(broker_api, "get_real_market_candles", lambda *_args, **_kwargs: [candle])
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: None)

    try:
        client.get("/api/v1/markets/XAUUSD/candles?timeframe=M5&limit=30")
        opened = client.post(
            "/api/v1/practice/orders",
            json={"symbol": "XAUUSD", "direction": "SELL", "volume": "0.01"},
        )
        ticket = opened.json()["position"]["ticket"]

        accepted = client.patch(
            f"/api/v1/practice/positions/{ticket}",
            json={"stop_loss": "3623.00", "take_profit": "3621.00"},
        )
        assert accepted.status_code == 200

        crossed = client.patch(
            f"/api/v1/practice/positions/{ticket}",
            json={"stop_loss": "3622.55", "take_profit": "3621.00"},
        )
        assert crossed.status_code == 422
        assert crossed.json()["detail"] == "Stop loss for SELL must be above current ask (3622.55)"
    finally:
        simulation_adapter.restore_state(previous_book)


def test_simulation_chart_does_not_fall_back_to_generated_prices_when_market_data_fails(monkeypatch):
    monkeypatch.setattr(runtime_store, "state", RuntimeState(broker="simulation"))

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("Market provider unavailable")

    monkeypatch.setattr(broker_api, "get_real_market_candles", unavailable)

    response = client.get("/api/v1/markets/EURUSD/candles?timeframe=M5&limit=30")

    assert response.status_code == 503
    assert response.json()["detail"] == "Market provider unavailable"


def test_mt5_market_candles_and_practice_quotes_use_the_live_broker_quote(monkeypatch):
    now = datetime.now(UTC)
    interval_seconds = 5 * 60
    candle_time = datetime.fromtimestamp(int(now.timestamp() // interval_seconds) * interval_seconds, UTC)
    history = [
        Candle(
            symbol="EURUSD",
            timeframe="M5",
            time=candle_time,
            open=Decimal("1.09000"),
            high=Decimal("1.09100"),
            low=Decimal("1.08900"),
            close=Decimal("1.09050"),
            volume=Decimal("100"),
        ),
    ]
    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            mt5_connected=True,
            account_id="123456",
            worker_last_seen=now,
            market_data=({
                "base_symbol": "EURUSD",
                "symbol": "EURUSDm",
                "bid": "1.10000",
                "ask": "1.10020",
                "time": now.isoformat(),
            },),
        ),
    )
    monkeypatch.setattr(broker_api, "get_mt5_candles", lambda *_args: ("EURUSDm", list(history)))
    monkeypatch.setattr(
        broker_api,
        "get_live_mt5_tick",
        lambda _symbol: Tick("EURUSD", Decimal("1.10000"), Decimal("1.10020"), now),
    )

    response = client.get("/api/v1/markets/EURUSD/candles?timeframe=M5&limit=30")

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSDm"
    assert body["data_source"] == "mt5"
    assert body["simulated"] is False
    latest = body["candles"][-1]
    assert latest["close"] == "1.10010"
    assert latest["high"] == "1.10020"
    assert latest["low"] == "1.08900"


def test_practice_adapter_uses_mt5_quotes_when_the_broker_is_connected(monkeypatch):
    now = datetime.now(UTC)
    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            mt5_connected=True,
            worker_last_seen=now,
            market_data=({
                "base_symbol": "EURUSD",
                "symbol": "EURUSDm",
                "bid": "1.10000",
                "ask": "1.10020",
                "time": now.isoformat(),
            },),
        ),
    )

    tick = simulation_adapter.get_tick("EURUSD")

    assert tick.bid == Decimal("1.10000")
    assert tick.ask == Decimal("1.10020")
    assert tick.time == now
    response = client.get("/api/v1/practice/markets")
    assert response.status_code == 200
    quotes = response.json()
    assert len(quotes) == 1
    assert quotes[0]["symbol"] == "EURUSD"
    assert quotes[0]["bid"] == "1.10000"
    assert quotes[0]["simulated"] is False


def test_practice_adapter_rejects_stale_mt5_quotes_without_simulation_fallback(monkeypatch):
    now = datetime.now(UTC)
    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            mt5_connected=True,
            worker_last_seen=now,
            market_data=({
                "base_symbol": "EURUSD",
                "symbol": "EURUSDm",
                "bid": "1.10000",
                "ask": "1.10020",
                "time": (now - timedelta(minutes=1)).isoformat(),
            },),
        ),
    )

    try:
        simulation_adapter.get_tick("EURUSD")
    except RuntimeError as error:
        assert "stale" in str(error)
    else:
        raise AssertionError("A stale MT5 quote must not fall back to simulated pricing")


def test_market_candle_endpoint_does_not_fallback_when_mt5_candles_are_missing(monkeypatch):
    previous_runtime = runtime_store.state
    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            mt5_connected=True,
            worker_last_seen=datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(broker_api, "get_mt5_candles", lambda _symbol, _timeframe: None)

    try:
        response = client.get("/api/v1/markets/EURUSD/candles?timeframe=M5")

        assert response.status_code == 503
        assert "No fresh MT5" in response.json()["detail"]
    finally:
        runtime_store.state = previous_runtime


def test_simulation_positions_endpoint_marks_practice_capability(monkeypatch):
    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: None)
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    try:
        response = client.get("/api/v1/positions")

        assert response.status_code == 200
        assert response.json()["connected"] is True
        assert response.json()["items"] == []
        assert response.json()["simulated"] is True
        assert response.json()["trading_mode"] == "paper_only"
        assert response.json()["can_trade_simulation"] is True
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_simulation_practice_trade_can_open_and_close_without_broker_orders(monkeypatch):
    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    runtime_store.connect_demo()
    monkeypatch.setattr(
        simulation_adapter,
        "get_tick",
        lambda symbol: Tick(
            symbol=symbol,
            bid=Decimal("1.10000"),
            ask=Decimal("1.10010"),
            time=datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: None)

    try:
        too_risky = client.post(
            "/api/v1/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "volume": "2",
                "stop_loss": "1.09910",
            },
        )
        assert too_risky.status_code == 422

        opened = client.post(
            "/api/v1/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "volume": "0.01",
                "stop_loss": "1.09910",
                "take_profit": "1.10210",
                "idempotency_key": "practice-order-test",
            },
        )

        assert opened.status_code == 200
        position = opened.json()["position"]
        assert position["simulated"] is True
        assert position["direction"] == "BUY"
        assert Decimal(position["price_open"]) == Decimal("1.10010")

        open_history = client.get("/api/v1/history").json()
        assert open_history["total"] == 1
        assert open_history["items"][0]["deal_type"] == "ENTRY"
        persisted_book = simulation_adapter.export_state()
        simulation_adapter.restore_state({"balance": "10000", "positions": [], "deals": []})
        simulation_adapter.restore_state(persisted_book)
        restored_history = client.get("/api/v1/history").json()
        assert restored_history["total"] == 1
        assert restored_history["items"][0]["order"] == position["ticket"]

        repeated = client.post(
            "/api/v1/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "volume": "0.01",
                "stop_loss": "1.09910",
                "take_profit": "1.10210",
                "idempotency_key": "practice-order-test",
            },
        )
        assert repeated.status_code == 200

        positions = client.get("/api/v1/positions").json()
        assert positions["can_trade_simulation"] is True
        assert positions["total"] == 1

        closed = client.post(f"/api/v1/positions/{position['ticket']}/close")
        assert closed.status_code == 200
        assert closed.json()["simulated"] is True
        assert closed.json()["deal"]["close_reason"] == "MANUAL"

        history = client.get("/api/v1/history").json()
        assert history["simulated"] is True
        assert history["total"] == 2
        assert history["items"][0]["deal_type"] == "EXIT"
        assert history["items"][1]["deal_type"] == "ENTRY"
        assert history["items"][0]["order"] == position["ticket"]
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_open_practice_trade_history_survives_runtime_restore(monkeypatch):
    class MemoryRedis:
        values: dict[str, str] = {}

        def set(self, key: str, value: str, ex: int) -> bool:
            self.values[key] = value
            return True

        def get(self, key: str) -> str | None:
            return self.values.get(key)

    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "deals": []})
    runtime_store.connect_demo()
    monkeypatch.setattr(persistent_runtime.Redis, "from_url", lambda *_args, **_kwargs: MemoryRedis())
    monkeypatch.setattr(
        simulation_adapter,
        "get_tick",
        lambda symbol: Tick(
            symbol=symbol,
            bid=Decimal("1.10000"),
            ask=Decimal("1.10010"),
            time=datetime.now(UTC),
        ),
    )

    try:
        opened = client.post(
            "/api/v1/practice/orders",
            json={"symbol": "EURUSD", "direction": "BUY", "volume": "0.01"},
        )
        assert opened.status_code == 200

        simulation_adapter.restore_state({"balance": "10000", "positions": [], "deals": []})
        runtime_store.state = RuntimeState()
        persistent_runtime.restore_runtime_state()

        history = client.get("/api/v1/history")
        assert history.status_code == 200
        assert history.json()["total"] == 1
        assert history.json()["items"][0]["deal_type"] == "ENTRY"
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_history_backfills_and_persists_entry_for_legacy_open_practice_position(monkeypatch):
    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    opened_at = datetime.now(UTC).isoformat()
    simulation_adapter.restore_state({
        "balance": "10000",
        "positions": [{
            "ticket": "SIM-LEGACY",
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": "0.01",
            "price_open": "1.10010",
            "price_current": "1.10000",
            "profit": "-0.01",
            "stop_loss": "0",
            "take_profit": "0",
            "initial_risk": "0",
            "open_time": opened_at,
            "simulated": True,
        }],
        "closed_deals": [],
    })
    monkeypatch.setattr(runtime_store, "state", RuntimeState(broker="simulation", mt5_connected=True))
    saves: list[dict] = []
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: saves.append(simulation_adapter.export_state()))

    try:
        history = client.get("/api/v1/history")
        repeated = client.get("/api/v1/history")

        assert history.status_code == 200
        assert history.json()["total"] == 1
        assert history.json()["items"][0]["deal_type"] == "ENTRY"
        assert history.json()["items"][0]["time"] == opened_at
        assert repeated.json()["total"] == 1
        assert len(saves) == 1
        assert saves[0]["deals"][0]["order"] == "SIM-LEGACY"
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_practice_account_works_without_broker_connection(monkeypatch):
    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(),
    )
    monkeypatch.setattr(
        simulation_adapter,
        "get_tick",
        lambda symbol: Tick(
            symbol=symbol,
            bid=Decimal("1.10000"),
            ask=Decimal("1.10010"),
            time=datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: None)

    try:
        status = client.get("/api/v1/practice/status")
        markets = client.get("/api/v1/practice/markets")
        opened = client.post(
            "/api/v1/practice/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "order_type": "MARKET",
                "volume": "0.01",
                "stop_price": None,
                "stop_loss": None,
                "take_profit": None,
            },
        )
        positions = client.get("/api/v1/practice/positions")

        assert status.status_code == 200
        assert status.json()["connected"] is True
        assert len(markets.json()) > 0
        assert opened.status_code == 200
        assert opened.json()["simulated"] is True
        assert simulation_adapter.export_state()["positions"], simulation_adapter.export_state()
        assert opened.json()["position"] is not None, opened.text
        assert positions.status_code == 200
        assert positions.json()["total"] == 1
        assert positions.json()["items"][0]["stop_loss"] == "0"
        assert runtime_store.state.broker == "none"

        closed = client.post(f"/api/v1/practice/positions/{opened.json()['position']['ticket']}/close")
        assert closed.status_code == 200
        practice_history = client.get("/api/v1/practice/history").json()
        assert practice_history["total"] == 2
        assert [deal["deal_type"] for deal in practice_history["items"]] == ["EXIT", "ENTRY"]

        missing_stop_price = client.post(
            "/api/v1/practice/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "order_type": "BUY_STOP",
                "volume": "0.01",
            },
        )
        wrong_stop_direction = client.post(
            "/api/v1/practice/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "order_type": "SELL_STOP",
                "volume": "0.01",
                "stop_price": "1.09900",
            },
        )
        assert missing_stop_price.status_code == 422
        assert wrong_stop_direction.status_code == 422

        pending = client.post(
            "/api/v1/practice/orders",
            json={
                "symbol": "EURUSD",
                "direction": "BUY",
                "order_type": "BUY_STOP",
                "volume": "0.01",
                "stop_price": "1.10100",
            },
        )
        assert pending.status_code == 200
        assert pending.json()["pending_order"]["order_type"] == "BUY_STOP"
        assert client.get("/api/v1/practice/positions").json()["pending_total"] == 1
        cancelled = client.delete(f"/api/v1/practice/orders/{pending.json()['pending_order']['ticket']}")
        assert cancelled.status_code == 200
        assert client.get("/api/v1/practice/positions").json()["pending_total"] == 0
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_practice_account_deposit_adds_funds_and_persists(monkeypatch):
    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    monkeypatch.setattr(runtime_store, "state", RuntimeState())
    saves: list[dict] = []
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: saves.append(simulation_adapter.export_state()))

    try:
        response = client.post("/api/v1/practice/account/deposit", json={"amount": "250.50"})
        invalid_amount = client.post("/api/v1/practice/account/deposit", json={"amount": "0"})

        assert response.status_code == 200
        assert response.json()["deposited"] == "250.50"
        assert response.json()["simulated"] is True
        assert response.json()["account"]["balance"] == "10250.50"
        assert invalid_amount.status_code == 422
        assert simulation_adapter.export_state()["balance"] == "10250.50"
        assert len(saves) == 1
        assert saves[0]["balance"] == "10250.50"
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_practice_position_can_be_modified_and_bulk_closed(monkeypatch):
    previous_runtime = runtime_store.state
    previous_book = simulation_adapter.export_state()
    simulation_adapter.restore_state({"balance": "10000", "positions": [], "closed_deals": []})
    monkeypatch.setattr(runtime_store, "state", RuntimeState())
    monkeypatch.setattr(
        simulation_adapter,
        "get_tick",
        lambda symbol: Tick(
            symbol=symbol,
            bid=Decimal("1.10000"),
            ask=Decimal("1.10010"),
            time=datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(broker_api, "save_runtime_state", lambda: None)

    try:
        opened_positions = []
        for direction in ("BUY", "SELL"):
            opened = client.post(
                "/api/v1/practice/orders",
                json={"symbol": "EURUSD", "direction": direction, "volume": "0.01"},
            )
            assert opened.status_code == 200
            opened_positions.append(opened.json()["position"])

        ticket = opened_positions[0]["ticket"]
        modified = client.patch(
            f"/api/v1/practice/positions/{ticket}",
            json={"stop_loss": "1.09900", "take_profit": "1.10100"},
        )
        assert modified.status_code == 200
        assert modified.json()["position"]["stop_loss"] == "1.09900"
        assert modified.json()["position"]["take_profit"] == "1.10100"

        invalid = client.patch(
            f"/api/v1/practice/positions/{ticket}",
            json={"stop_loss": "1.10000", "take_profit": "1.10100"},
        )
        assert invalid.status_code == 422

        partial = client.post(
            "/api/v1/practice/positions/close-bulk",
            json={"tickets": [opened_positions[0]["ticket"], "missing-ticket"]},
        )
        assert partial.status_code == 404
        assert client.get("/api/v1/practice/positions").json()["total"] == 2

        closed = client.post(
            "/api/v1/practice/positions/close-bulk",
            json={"tickets": [position["ticket"] for position in opened_positions]},
        )
        assert closed.status_code == 200
        assert closed.json()["closed"] == 2
        assert client.get("/api/v1/practice/positions").json()["total"] == 0
    finally:
        runtime_store.state = previous_runtime
        simulation_adapter.restore_state(previous_book)


def test_simulation_history_endpoint_is_empty_and_marked_simulated(sqlite_database):
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    response = client.get("/api/v1/history")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["connected"] is True
    assert response.json()["simulated"] is True


def test_demo_connection_and_engine_controls():
    connect = client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    assert connect.status_code == 200
    assert connect.json()["connected"] is True
    assert connect.json()["environment"] == "demo"
    assert connect.json()["simulated"] is True

    start = client.post("/api/v1/engine/start")
    assert start.status_code == 200
    assert start.json()["running"] is True

    stop = client.post("/api/v1/engine/stop")
    assert stop.status_code == 200
    assert stop.json()["running"] is False


def test_persistent_runtime_restores_simulation_and_engine():
    from app.core.persistent_runtime import restore_runtime_state, save_runtime_state
    from app.core.runtime import runtime_store

    runtime_store.connect_demo()
    runtime_store.start_engine()
    save_runtime_state()

    runtime_store.disconnect()
    restore_runtime_state()

    assert runtime_store.state.broker == "simulation"
    assert runtime_store.state.mt5_connected is True
    assert runtime_store.state.engine_running is True


def test_mt5_market_quotes_are_read_only_and_include_spread(monkeypatch):
    from app.core.runtime import RuntimeState, runtime_store

    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            environment="demo",
            account_id="123456",
            mt5_connected=True,
            market_data=(
                {
                    "base_symbol": "EURUSD",
                    "symbol": "EURUSDm",
                    "bid": "1.10000",
                    "ask": "1.10012",
                    "digits": 5,
                    "time": datetime.now(UTC).isoformat(),
                },
            ),
            worker_last_seen=datetime.now(UTC),
        ),
    )

    response = client.get("/api/v1/markets")

    assert response.status_code == 200
    quote = response.json()[0]
    assert quote["symbol"] == "EURUSDm"
    assert quote["spread"] == "0.00012"
    assert quote["simulated"] is False
    assert quote["execution_mode"] == "paper_only"
    status = client.get("/api/v1/accounts/status")
    assert status.json()["simulated"] is False


def test_mt5_connect_requires_encryption_key_and_never_echoes_password(monkeypatch):
    from app.api.v1 import broker
    from app.core.credential_encryption import CredentialEncryptionError

    def encryption_unavailable(_: bytes) -> str:
        raise CredentialEncryptionError("MT5_ENCRYPTION_KEY is not configured")

    monkeypatch.setattr(broker, "encrypt_credentials", encryption_unavailable)
    response = client.post(
        "/api/v1/accounts/connect",
        json={"broker": "mt5", "account_id": "123456", "password": "top-secret", "server": "Exness-MT5Demo"},
    )
    assert response.status_code == 503
    assert "top-secret" not in response.text


def test_worker_claim_requires_configured_worker_token(monkeypatch):
    from app.api.v1 import broker
    from app.core.config import Settings

    monkeypatch.setattr(broker, "get_settings", lambda: Settings(mt5_worker_token=""))
    response = client.post("/api/v1/worker/mt5/claim")
    assert response.status_code == 503
