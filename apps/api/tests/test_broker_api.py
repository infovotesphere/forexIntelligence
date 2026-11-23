from decimal import Decimal

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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
    assert {"EURUSD", "GBPUSD", "XAUUSD"} <= symbols
    eurusd = next(instrument for instrument in instruments if instrument["symbol"] == "EURUSD")
    assert Decimal(eurusd["ask"]) > Decimal(eurusd["bid"])
    assert Decimal(eurusd["spread"]) == Decimal(eurusd["ask"]) - Decimal(eurusd["bid"])
    assert eurusd["simulated"] is True


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
