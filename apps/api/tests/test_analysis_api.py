from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_analysis_endpoint_returns_completed_candle_context():
    response = client.get("/api/v1/analysis/EURUSD", params={"timeframe": "H1"})
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["timeframe"] == "H1"
    assert body["simulated"] is True
    assert "indicators" in body
    assert "strategy_signals" in body


def test_analysis_rejects_unknown_symbol():
    response = client.get("/api/v1/analysis/UNKNOWN")
    assert response.status_code == 404
