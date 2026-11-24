from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.auth import AUTH_COOKIE_NAME
from app.core.runtime import RuntimeState, runtime_store
from app.core.security import create_access_token
from shared.contracts.broker import Candle
from app.main import app

client = TestClient(app, cookies={AUTH_COOKIE_NAME: create_access_token("test@example.com", "administrator")})


def test_backtesting_endpoint_returns_simulation_model_and_summary():
    previous_state = runtime_store.state
    runtime_store.connect_demo()
    try:
        response = client.post(
            "/api/v1/backtesting/run",
            json={"symbol": "EURUSD", "timeframe": "H1", "strategy": "trend_following", "bars": 260},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["simulated"] is True
        assert result["data_source"] == "simulation"
        assert result["bars_tested"] >= 200
        assert len(result["candles"]) == result["bars_tested"]
        replay_candles = result["candles"][:100]
        assert any(Decimal(candle["close"]) > Decimal(candle["open"]) for candle in replay_candles)
        assert any(Decimal(candle["close"]) < Decimal(candle["open"]) for candle in replay_candles)
        assert result["strategy"] == "trend_following"
        assert "Spread, slippage, commissions" in result["execution_model"]
        assert {"wins", "losses", "net_r", "max_drawdown_r"} <= result["summary"].keys()
        assert isinstance(result["equity_curve"], list)
        assert len(result["equity_curve"]) == result["summary"]["resolved_trades"]
    finally:
        runtime_store.state = previous_state


def test_backtesting_accepts_one_minute_bars(monkeypatch):
    from app.api.v1 import backtesting

    previous_state = runtime_store.state
    runtime_store.connect_demo()
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    candles = [
        Candle(
            symbol="EURUSD",
            timeframe="M1",
            time=now - timedelta(minutes=31 - index),
            open=Decimal("1.10000"),
            high=Decimal("1.10100"),
            low=Decimal("1.09900"),
            close=Decimal("1.10050"),
            volume=Decimal("100"),
        )
        for index in range(31)
    ]
    monkeypatch.setattr(backtesting, "get_real_market_candles", lambda _symbol, _timeframe: candles)

    try:
        response = client.post(
            "/api/v1/backtesting/run",
            json={"symbol": "EURUSD", "timeframe": "M1", "strategy": "trend_following", "bars": 30},
        )

        assert response.status_code == 200
        assert response.json()["timeframe"] == "M1"
        assert response.json()["bars_tested"] == 30
    finally:
        runtime_store.state = previous_state


def test_backtesting_rejects_unknown_instrument_and_invalid_window():
    previous_state = runtime_store.state
    runtime_store.connect_demo()
    try:
        unknown = client.post("/api/v1/backtesting/run", json={"symbol": "UNKNOWN"})
        too_many = client.post("/api/v1/backtesting/run", json={"symbol": "EURUSD", "bars": 2001})

        assert unknown.status_code == 404
        assert too_many.status_code == 422
    finally:
        runtime_store.state = previous_state


def test_backtesting_uses_connected_mt5_candles_and_excludes_forming_bar(monkeypatch):
    from app.api.v1 import backtesting

    now = datetime.now(UTC)
    candles = [
        Candle(
            symbol="EURUSDm",
            timeframe="H1",
            time=now - timedelta(hours=500 - index),
            open=Decimal("1.10000"),
            high=Decimal("1.10100"),
            low=Decimal("1.09900"),
            close=Decimal("1.10050"),
            volume=Decimal("100"),
        )
        for index in range(2001)
    ]
    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            environment="demo",
            account_id="123456",
            server="Exness-MT5Demo",
            mt5_connected=True,
            market_data=({"base_symbol": "EURUSD", "symbol": "EURUSDm", "tick_size": "0.00001"},),
            worker_last_seen=now,
        ),
    )
    monkeypatch.setattr(backtesting, "get_mt5_candles", lambda _symbol, _timeframe: ("EURUSDm", candles))

    response = client.post(
        "/api/v1/backtesting/run",
        json={"symbol": "EURUSD", "timeframe": "H1", "strategy": "trend_following", "bars": 2000},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["simulated"] is False
    assert result["data_source"] == "mt5"
    assert result["symbol"] == "EURUSDm"
    assert result["bars_tested"] == 2000
    assert len(result["candles"]) == 2000
    assert result["candles"][-1]["time"] == candles[-2].time.isoformat()
    assert "read-only MT5 broker history" in result["execution_model"]


def test_backtesting_does_not_fall_back_when_mt5_history_is_unavailable(monkeypatch):
    from app.api.v1 import backtesting

    monkeypatch.setattr(
        runtime_store,
        "state",
        RuntimeState(
            broker="mt5",
            environment="demo",
            account_id="123456",
            server="Exness-MT5Demo",
            mt5_connected=True,
            worker_last_seen=datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(backtesting, "get_mt5_candles", lambda _symbol, _timeframe: None)

    response = client.post("/api/v1/backtesting/run", json={"symbol": "EURUSD"})

    assert response.status_code == 503
    assert response.json()["detail"] == "No MT5 H1 candle history is available for EURUSD"


def test_backtesting_requires_an_explicit_broker_account(monkeypatch):
    monkeypatch.setattr(runtime_store, "state", RuntimeState())

    response = client.post("/api/v1/backtesting/run", json={"symbol": "EURUSD"})

    assert response.status_code == 503
    assert "No broker account is selected" in response.json()["detail"]
