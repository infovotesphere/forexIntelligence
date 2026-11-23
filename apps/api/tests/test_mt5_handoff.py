from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.api.v1 import broker
from app.core.config import Settings
from app.core.runtime import runtime_store
from app.main import app

client = TestClient(app)


def test_mt5_demo_credentials_are_encrypted_claimed_once_and_worker_authenticated(monkeypatch):
    previous_state = runtime_store.state
    key = Fernet.generate_key()
    cipher = Fernet(key)
    worker_token = "test-worker-token"
    monkeypatch.setattr(
        broker,
        "get_settings",
        lambda: Settings(mt5_worker_token=worker_token, live_trading_enabled=False),
    )
    monkeypatch.setattr(
        broker,
        "encrypt_credentials",
        lambda value: cipher.encrypt(value).decode("ascii"),
    )
    monkeypatch.setattr(
        broker,
        "decrypt_credentials",
        lambda value: cipher.decrypt(value.encode("ascii")),
    )

    try:
        connect = client.post(
            "/api/v1/accounts/connect",
            json={
                "broker": "mt5",
                "account_id": "123456",
                "password": "do-not-return-this",
                "server": "Exness-MT5Demo",
            },
        )
        assert connect.status_code == 200
        assert connect.json()["connected"] is False
        assert connect.json()["simulated"] is True
        assert "do-not-return-this" not in connect.text

        rejected = client.post("/api/v1/worker/mt5/claim")
        assert rejected.status_code == 401

        headers = {"Authorization": f"Bearer {worker_token}"}
        claim = client.post("/api/v1/worker/mt5/claim", headers=headers)
        assert claim.status_code == 200
        assert claim.json() == {
            "account_id": "123456",
            "password": "do-not-return-this",
            "server": "Exness-MT5Demo",
            "environment": "demo",
        }
        assert client.post("/api/v1/worker/mt5/claim", headers=headers).status_code == 204

        status_response = client.post(
            "/api/v1/worker/mt5/status",
            headers=headers,
            json={
                "connected": True,
                "account_id": "123456",
                "server": "Exness-MT5Demo",
                "environment": "demo",
                "currency": "USD",
                "balance": "1000.00",
                "equity": "1005.00",
                "market_data": [{
                    "base_symbol": "EURUSD",
                    "symbol": "EURUSDm",
                    "bid": "1.10000",
                    "ask": "1.10010",
                    "time": "2026-11-23T14:00:00+00:00",
                }],
                "message": "MT5 demo connected; trading remains paper-only",
            },
        )
        assert status_response.status_code == 200
        current = client.get("/api/v1/accounts/status").json()
        assert current["connected"] is True
        assert current["broker"] == "mt5"
        assert current["trading_mode"] == "paper_only"
        assert current["account"]["balance"] == "1000.00"
        assert current["trading_mode"] == "paper_only"
        market = client.get("/api/v1/markets").json()
        assert market[0]["symbol"] == "EURUSDm"
        assert market[0]["execution_mode"] == "paper_only"
    finally:
        runtime_store.state = previous_state


def test_live_mt5_requires_explicit_readonly_confirmation_and_never_starts_engine(monkeypatch):
    previous_state = runtime_store.state
    cipher = Fernet(Fernet.generate_key())
    worker_token = "live-test-worker-token"
    monkeypatch.setattr(
        broker,
        "get_settings",
        lambda: Settings(mt5_worker_token=worker_token, live_trading_enabled=True),
    )
    monkeypatch.setattr(
        broker,
        "encrypt_credentials",
        lambda value: cipher.encrypt(value).decode("ascii"),
    )
    monkeypatch.setattr(
        broker,
        "decrypt_credentials",
        lambda value: cipher.decrypt(value.encode("ascii")),
    )
    headers = {"Authorization": f"Bearer {worker_token}"}

    try:
        body = {
            "broker": "mt5",
            "environment": "live",
            "account_id": "654321",
            "password": "live-password",
            "server": "Exness-MT5Real",
        }
        unconfirmed = client.post("/api/v1/accounts/connect", json=body)
        assert unconfirmed.status_code == 422

        body["live_read_only_confirmed"] = True
        connected = client.post("/api/v1/accounts/connect", json=body)
        assert connected.status_code == 200
        assert connected.json()["environment"] == "live"
        assert connected.json()["live_trading_enabled"] is False
        assert connected.json()["trading_mode"] == "paper_only"

        claim = client.post("/api/v1/worker/mt5/claim", headers=headers)
        assert claim.status_code == 200
        assert claim.json()["environment"] == "live"
        assert claim.json()["password"] == "live-password"

        worker_status = client.post(
            "/api/v1/worker/mt5/status",
            headers=headers,
            json={
                "connected": True,
                "account_id": "654321",
                "server": "Exness-MT5Real",
                "environment": "live",
                "message": "MT5 live connected; trading remains paper-only",
            },
        )
        assert worker_status.status_code == 200

        engine = client.post("/api/v1/engine/start")
        assert engine.status_code == 200
        assert engine.json()["running"] is False
        assert engine.json()["live_trading_enabled"] is False
        assert "read-only" in engine.json()["message"]
    finally:
        runtime_store.state = previous_state
