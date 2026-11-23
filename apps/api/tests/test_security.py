import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    digest = hash_password("phase-one-password")
    assert digest != "phase-one-password"
    assert verify_password("phase-one-password", digest)
    assert not verify_password("wrong-password", digest)


def test_jwt_round_trip():
    token = create_access_token("test@example.com", "administrator")
    claims = decode_access_token(token)
    assert claims["sub"] == "test@example.com"
    assert claims["role"] == "administrator"


def test_non_development_requires_strong_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="short-secret")

    Settings(environment="production", jwt_secret="random-production-secret-value-123456")
