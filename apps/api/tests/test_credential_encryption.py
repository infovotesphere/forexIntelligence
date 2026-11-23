import json
from cryptography.fernet import Fernet

from app.core.config import Settings
from app.core import credential_encryption


def test_mt5_credentials_are_encrypted_and_recoverable(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(credential_encryption, "get_settings", lambda: Settings(mt5_encryption_key=key))
    payload = json.dumps({"account_id": "123456", "password": "secret", "server": "demo"}).encode()

    encrypted = credential_encryption.encrypt_credentials(payload)

    assert "secret" not in encrypted
    assert credential_encryption.decrypt_credentials(encrypted) == payload
