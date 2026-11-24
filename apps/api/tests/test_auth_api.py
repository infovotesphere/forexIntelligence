from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import AUTH_COOKIE_NAME
from app.core.database import Base, get_db
from app.core.security import hash_password, verify_password
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


def test_registration_creates_viewer_account_after_admin_is_provisioned(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, test_session = auth_client
    unavailable = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "display_name": "New User",
            "password": "a-secure-registration-password",
        },
    )
    assert unavailable.status_code == 503

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

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "New@Example.com",
            "display_name": "  New User  ",
            "password": "a-secure-registration-password",
        },
    )
    assert registered.status_code == 201
    assert registered.json() == {"email": "new@example.com", "role": "viewer"}
    assert client.get("/api/v1/auth/profile").json() == {
        "email": "new@example.com",
        "display_name": "New User",
        "role": "viewer",
    }
    assert client.post("/api/v1/accounts/connect", json={"broker": "simulation"}).status_code == 403
    assert client.get("/api/v1/auth/users").status_code == 403
    assert client.post(
        "/api/v1/auth/users",
        json={
            "email": "another@example.com",
            "display_name": "Another User",
            "password": "another-secure-password",
        },
    ).status_code == 403

    with test_session() as db:
        user = db.scalar(select(User).where(User.email == "new@example.com"))
        assert user is not None
        assert user.role == "viewer"
        assert user.is_active is True
        assert user.password_hash != "a-secure-registration-password"


def test_profile_and_password_can_be_updated_and_new_email_remains_authenticated(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, test_session = auth_client
    with test_session() as db:
        db.add(
            User(
                email="user@example.com",
                display_name="Original Name",
                password_hash=hash_password("a-secure-test-password"),
                role="viewer",
                is_active=True,
            )
        )
        db.commit()
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "a-secure-test-password"},
    ).status_code == 200

    updated = client.patch(
        "/api/v1/auth/profile",
        json={"email": "updated@example.com", "display_name": "Updated Name"},
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "updated@example.com"
    assert updated.json()["display_name"] == "Updated Name"
    assert client.get("/api/v1/auth/me").json()["email"] == "updated@example.com"

    changed = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "a-secure-test-password",
            "new_password": "a-different-secure-password",
        },
    )
    assert changed.status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "updated@example.com", "password": "a-secure-test-password"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "updated@example.com", "password": "a-different-secure-password"},
    ).status_code == 200


def test_administrator_can_manage_users_without_disabling_last_admin(
    auth_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, test_session = auth_client
    with test_session() as db:
        db.add_all(
            [
                User(
                    email="admin@example.com",
                    password_hash=hash_password("a-secure-test-password"),
                    role="administrator",
                    is_active=True,
                ),
                User(
                    email="viewer@example.com",
                    password_hash=hash_password("another-secure-password"),
                    role="viewer",
                    is_active=True,
                ),
            ]
        )
        db.commit()
        viewer = db.scalar(select(User).where(User.email == "viewer@example.com"))
        assert viewer is not None
        viewer_id = str(viewer.id)

    assert client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "a-secure-test-password"},
    ).status_code == 200
    users = client.get("/api/v1/auth/users")
    assert users.status_code == 200
    assert len(users.json()) == 2

    created = client.post(
        "/api/v1/auth/users",
        json={
            "email": "new-user@example.com",
            "display_name": "New User",
            "password": "a-temporary-secure-password",
            "role": "viewer",
        },
    )
    assert created.status_code == 201
    assert created.json()["email"] == "new-user@example.com"
    assert created.json()["role"] == "viewer"
    deleted = client.delete(f"/api/v1/auth/users/{created.json()['id']}")
    assert deleted.status_code == 204
    admin_id = next(user["id"] for user in users.json() if user["email"] == "admin@example.com")
    assert client.delete(f"/api/v1/auth/users/{admin_id}").status_code == 409

    promoted = client.patch(
        f"/api/v1/auth/users/{viewer_id}",
        json={
            "email": "updated-viewer@example.com",
            "display_name": "Updated Viewer",
            "role": "administrator",
            "password": "a-reset-secure-password",
        },
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "administrator"
    assert promoted.json()["email"] == "updated-viewer@example.com"
    assert promoted.json()["display_name"] == "Updated Viewer"
    with test_session() as db:
        updated_viewer = db.scalar(select(User).where(User.email == "updated-viewer@example.com"))
        assert updated_viewer is not None
        assert verify_password("a-reset-secure-password", updated_viewer.password_hash)
    disabled = client.patch(f"/api/v1/auth/users/{viewer_id}", json={"is_active": False})
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    last_admin = client.patch(f"/api/v1/auth/users/{admin_id}", json={"is_active": False})
    assert last_admin.status_code == 409
