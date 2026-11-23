from fastapi.testclient import TestClient

from app.core.auth import AUTH_COOKIE_NAME
from app.core.security import create_access_token
from app.main import app

client = TestClient(app, cookies={AUTH_COOKIE_NAME: create_access_token("test@example.com", "administrator")})


def test_backtesting_endpoint_returns_simulation_model_and_summary():
    response = client.post(
        "/api/v1/backtesting/run",
        json={"symbol": "EURUSD", "timeframe": "H1", "strategy": "trend_following", "bars": 260},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["simulated"] is True
    assert result["bars_tested"] >= 200
    assert result["strategy"] == "trend_following"
    assert "Spread, slippage, commissions" in result["execution_model"]
    assert {"wins", "losses", "net_r", "max_drawdown_r"} <= result["summary"].keys()


def test_backtesting_rejects_unknown_instrument_and_invalid_window():
    unknown = client.post("/api/v1/backtesting/run", json={"symbol": "UNKNOWN"})
    too_many = client.post("/api/v1/backtesting/run", json={"symbol": "EURUSD", "bars": 501})

    assert unknown.status_code == 404
    assert too_many.status_code == 422
