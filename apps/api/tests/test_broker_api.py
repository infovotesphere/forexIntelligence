from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from shared.contracts.broker import Tick
from app.api.v1 import broker as broker_api
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


def test_market_candle_endpoint_returns_simulated_preview_without_broker(monkeypatch):
    previous_runtime = runtime_store.state
    monkeypatch.setattr(runtime_store, "state", RuntimeState())

    try:
        response = client.get("/api/v1/markets/EURUSD/candles?timeframe=M5&limit=30")

        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "EURUSD"
        assert body["timeframe"] == "M5"
        assert body["data_source"] == "simulation"
        assert body["simulated"] is True
        assert len(body["candles"]) == 30
        assert set(body["candles"][0]) == {"time", "open", "high", "low", "close", "volume"}
    finally:
        runtime_store.state = previous_runtime


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
        assert history["total"] == 1
        assert history["items"][0]["order"] == position["ticket"]
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
        assert client.get("/api/v1/practice/history").json()["total"] == 1

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
