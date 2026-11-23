from datetime import UTC, datetime, timedelta

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
