from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_position_size_rounds_down_to_volume_step_and_stays_within_risk():
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    response = client.post(
        "/api/v1/risk/position-size",
        json={"symbol": "EURUSD", "entry": "1.10000", "stop_loss": "1.09875"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["volume"] == "0.8"
    assert Decimal(result["risk_budget"]) == Decimal("100")
    assert Decimal(result["estimated_risk"]) == Decimal("100")
    assert result["risk_within_budget"] is True
    assert result["simulated"] is True


def test_position_size_never_rounds_up_to_broker_minimum():
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    response = client.post(
        "/api/v1/risk/position-size",
        json={"symbol": "EURUSD", "entry": "1.10000", "stop_loss": "1.30000"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["volume"] == "0"
    assert result["estimated_risk"] == "0"
    assert result["reason"]


def test_position_size_rejects_risk_above_project_limit():
    client.post("/api/v1/accounts/connect", json={"broker": "simulation"})
    response = client.post(
        "/api/v1/risk/position-size",
        json={
            "symbol": "EURUSD",
            "entry": "1.10000",
            "stop_loss": "1.09900",
            "risk_percent": "1.01",
        },
    )

    assert response.status_code == 422


def test_position_size_requires_connected_account():
    from app.core.runtime import runtime_store

    runtime_store.disconnect()
    response = client.post(
        "/api/v1/risk/position-size",
        json={"symbol": "EURUSD", "entry": "1.10000", "stop_loss": "1.09900"},
    )

    assert response.status_code == 409
