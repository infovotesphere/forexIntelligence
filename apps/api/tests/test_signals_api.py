from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_generate_signals_endpoint():
    response = client.post("/api/v1/signals/generate", params={"symbol": "EURUSD", "timeframe": "H1"})
    assert response.status_code == 200
    body = response.json()
    assert body["simulated"] is True
    assert isinstance(body["items"], list)


def test_unknown_symbol_is_rejected():
    response = client.post("/api/v1/signals/generate", params={"symbol": "UNKNOWN"})
    assert response.status_code == 404
