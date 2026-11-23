from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from app.core.auth import AUTH_COOKIE_NAME
from app.core.security import create_access_token
from app.core.runtime import runtime_store
from app.main import app

client = TestClient(app, cookies={AUTH_COOKIE_NAME: create_access_token("test@example.com", "administrator")})


def test_analysis_endpoint_returns_completed_candle_context():
    response = client.get("/api/v1/analysis/EURUSD", params={"timeframe": "H1"})
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["timeframe"] == "H1"
    assert body["simulated"] is True
    assert "indicators" in body
    assert "strategy_signals" in body
    assert body["multi_timeframe"]["consensus"] in {"bullish", "bearish", "neutral"}
    assert set(body["multi_timeframe"]["timeframes"]) == {"M5", "M15", "M30", "H1", "H4", "D1"}


def test_analysis_rejects_unknown_symbol():
    response = client.get("/api/v1/analysis/UNKNOWN")
    assert response.status_code == 404


def test_mt5_analysis_uses_worker_candles_and_reports_missing_intervals():
    previous_state = runtime_store.state
    runtime_store.configure_mt5_account("123456", "Exness-MT5Demo", "demo", "encrypted")
    now = datetime.now(UTC)
    snapshots = []
    for timeframe, minutes in {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}.items():
        snapshots.append({
            "base_symbol": "EURUSD",
            "symbol": "EURUSDm",
            "timeframe": timeframe,
            "candles": [
                {
                    "time": (now - timedelta(minutes=minutes * (3 - index))).isoformat(),
                    "open": str(Decimal("1.10000") + Decimal(index) / 10000),
                    "high": str(Decimal("1.10020") + Decimal(index) / 10000),
                    "low": str(Decimal("1.09980") + Decimal(index) / 10000),
                    "close": str(Decimal("1.10010") + Decimal(index) / 10000),
                    "volume": "100",
                }
                for index in range(3)
            ],
        })
    try:
        runtime_store.update_mt5_status(
            connected=True,
            account_id="123456",
            server="Exness-MT5Demo",
            environment="demo",
            message="connected",
            market_candles=snapshots,
        )

        response = client.get("/api/v1/analysis/EURUSD", params={"timeframe": "H1"})

        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "EURUSDm"
        assert body["simulated"] is False
        assert body["data_source"] == "mt5"
        assert body["missing_timeframes"] == []
        assert set(body["multi_timeframe"]["timeframes"]) == {"M5", "M15", "M30", "H1", "H4", "D1"}
    finally:
        runtime_store.state = previous_state


def test_mt5_analysis_does_not_fall_back_to_simulation_when_candles_are_missing():
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
        response = client.get("/api/v1/analysis/EURUSD")
        assert response.status_code == 503
        assert "No MT5" in response.json()["detail"]
    finally:
        runtime_store.state = previous_state


def test_stale_mt5_candle_snapshots_are_not_used():
    previous_state = runtime_store.state
    runtime_store.configure_mt5_account("123456", "Exness-MT5Demo", "demo", "encrypted")
    now = datetime.now(UTC)
    runtime_store.update_mt5_status(
        connected=True,
        account_id="123456",
        server="Exness-MT5Demo",
        environment="demo",
        message="connected",
        market_candles=[{
            "base_symbol": "EURUSD",
            "symbol": "EURUSDm",
            "timeframe": "H1",
            "candles": [],
        }],
    )
    stale_snapshot = {
        **runtime_store.state.market_candles[0],
        "received_at": (now - timedelta(seconds=181)).isoformat(),
    }
    runtime_store.state = replace(runtime_store.state, market_candles=(stale_snapshot,))
    try:
        response = client.get("/api/v1/analysis/EURUSD", params={"timeframe": "H1"})
        assert response.status_code == 503
        assert "No MT5" in response.json()["detail"]
    finally:
        runtime_store.state = previous_state
