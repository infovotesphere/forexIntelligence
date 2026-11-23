from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_reports_safe_defaults():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["live_trading"] is False


def test_api_root_has_public_entry_points():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["documentation"] == "/docs"
