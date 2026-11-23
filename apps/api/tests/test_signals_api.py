from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from app.core.auth import AUTH_COOKIE_NAME
from app.core.security import create_access_token
from app.core.runtime import runtime_store
from app.main import app

client = TestClient(app, cookies={AUTH_COOKIE_NAME: create_access_token("test@example.com", "administrator")})


def test_signal_list_accepts_canonical_and_trailing_slash_paths():
    canonical = client.get("/api/v1/signals")
    trailing_slash = client.get("/api/v1/signals/")

    assert canonical.status_code == 200
    assert trailing_slash.status_code == 200
    assert canonical.json().keys() == trailing_slash.json().keys()


def test_generate_signals_endpoint():
    response = client.post("/api/v1/signals/generate", params={"symbol": "EURUSD", "timeframe": "H1"})
    assert response.status_code == 200
    body = response.json()
    assert body["simulated"] is True
    assert isinstance(body["items"], list)


def test_unknown_symbol_is_rejected():
    response = client.post("/api/v1/signals/generate", params={"symbol": "UNKNOWN"})
    assert response.status_code == 404


def test_expired_signal_is_reported_as_expired(monkeypatch):
    from app.api.v1 import signals

    monkeypatch.setattr(
        signals,
        "signal_store",
        [{
            "signal_id": "expired-test",
            "status": "VALIDATED",
            "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }],
    )

    response = client.get("/api/v1/signals/", params={"status": "EXPIRED"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "EXPIRED"


def test_mt5_signal_generation_uses_broker_history_and_tick_size(monkeypatch):
    from app.api.v1 import signals

    previous_state = runtime_store.state
    observed = {}

    def capture_input(symbol, timeframe, candles, strategies, tick_size):
        observed.update(symbol=symbol, timeframe=timeframe, candles=candles, tick_size=tick_size)
        return []

    monkeypatch.setattr(signals, "generate_validated_signals", capture_input)
    runtime_store.configure_mt5_account("123456", "Exness-MT5Demo", "demo", "encrypted")
    now = datetime.now(UTC)
    snapshot = {
        "base_symbol": "EURUSD",
        "symbol": "EURUSDm",
        "timeframe": "H1",
        "candles": [
            {
                "time": (now - timedelta(hours=3 - index)).isoformat(),
                "open": str(Decimal("1.10000") + Decimal(index) / 10000),
                "high": str(Decimal("1.10020") + Decimal(index) / 10000),
                "low": str(Decimal("1.09980") + Decimal(index) / 10000),
                "close": str(Decimal("1.10010") + Decimal(index) / 10000),
                "volume": "100",
            }
            for index in range(3)
        ],
    }
    try:
        runtime_store.update_mt5_status(
            connected=True,
            account_id="123456",
            server="Exness-MT5Demo",
            environment="demo",
            message="connected",
            market_data=[{
                "base_symbol": "EURUSD",
                "symbol": "EURUSDm",
                "tick_size": "0.00001",
                "bid": "1.10000",
                "ask": "1.10010",
                "time": now.isoformat(),
            }],
            market_candles=[snapshot],
        )

        response = client.post(
            "/api/v1/signals/generate",
            params={"symbol": "EURUSD", "timeframe": "H1"},
        )

        assert response.status_code == 200
        assert response.json()["simulated"] is False
        assert response.json()["data_source"] == "mt5"
        assert observed["symbol"] == "EURUSDm"
        assert observed["timeframe"] == "H1"
        assert len(observed["candles"]) == 3
        assert observed["tick_size"] == Decimal("0.00001")
    finally:
        runtime_store.state = previous_state


def test_mt5_signal_generation_refuses_simulation_fallback():
    previous_state = runtime_store.state
    runtime_store.configure_mt5_account("123456", "Exness-MT5Demo", "demo", "encrypted")
    try:
        runtime_store.update_mt5_status(
            connected=True,
            account_id="123456",
            server="Exness-MT5Demo",
            environment="demo",
            message="connected",
        )
        response = client.post(
            "/api/v1/signals/generate",
            params={"symbol": "EURUSD", "timeframe": "H1"},
        )
        assert response.status_code == 503
        assert "No MT5" in response.json()["detail"]
    finally:
        runtime_store.state = previous_state
