from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import AUTH_COOKIE_NAME
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User


@pytest.fixture
def auth_client() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Iterator[Session]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, test_session
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_application_api_requires_session_but_health_is_public(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = auth_client
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/markets").status_code == 401


def test_login_issues_http_only_cookie_and_logout_clears_session(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, test_session = auth_client
    with test_session() as db:
        db.add(
            User(
                email="admin@example.com",
                password_hash=hash_password("a-secure-test-password"),
                role="administrator",
                is_active=True,
            )
        )
        db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "a-secure-test-password"},
    )

    assert login.status_code == 200
    assert login.json() == {"email": "admin@example.com", "role": "administrator"}
    cookie = login.headers["set-cookie"]
    assert f"{AUTH_COOKIE_NAME}=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "access_token" not in login.json()
    assert client.get("/api/v1/auth/me").json() == {
        "email": "admin@example.com",
        "role": "administrator",
    }

    assert client.post("/api/v1/auth/logout").json() == {"logged_out": True}
    assert client.get("/api/v1/markets").status_code == 401


def test_login_rejects_bad_credentials_and_requires_provisioned_user(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, test_session = auth_client
    not_provisioned = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "a-secure-test-password"},
    )
    assert not_provisioned.status_code == 503

    with test_session() as db:
        db.add(
            User(
                email="admin@example.com",
                password_hash=hash_password("a-secure-test-password"),
                role="administrator",
                is_active=True,
            )
        )
        db.commit()

    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "incorrect-password"},
    )
    assert invalid.status_code == 401
    assert invalid.headers.get("set-cookie") is None
