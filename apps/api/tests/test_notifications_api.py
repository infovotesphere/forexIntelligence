from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.auth import AUTH_COOKIE_NAME
from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import app


client = TestClient(app, cookies={AUTH_COOKIE_NAME: create_access_token("test@example.com", "administrator")})


def test_notification_status_reports_configuration_without_token():
    with patch("app.api.v1.notifications.get_settings") as get_settings_mock:
        get_settings_mock.return_value = get_settings().model_copy(
            update={"telegram_bot_token": "secret-token", "telegram_chat_id": "123456789"}
        )
        response = client.get("/api/v1/notifications/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["provider"] == "Telegram"
    assert body["chat_id"] == "…6789"
    assert "secret-token" not in response.text


def test_notification_test_rejects_missing_configuration():
    with patch("app.api.v1.notifications.get_settings") as get_settings_mock:
        get_settings_mock.return_value = get_settings().model_copy(
            update={"telegram_bot_token": "", "telegram_chat_id": ""}
        )
        response = client.post("/api/v1/notifications/test")

    assert response.status_code == 400
    assert response.json()["detail"] == "Telegram is not configured"


def test_notification_test_delivers_when_configured():
    with patch("app.api.v1.notifications.get_settings") as get_settings_mock, patch(
        "app.api.v1.notifications.httpx.post"
    ) as telegram_post:
        get_settings_mock.return_value = get_settings().model_copy(
            update={"telegram_bot_token": "secret-token", "telegram_chat_id": "123456789"}
        )
        telegram_post.return_value.status_code = 200
        response = client.post("/api/v1/notifications/test")

    assert response.status_code == 200
    assert response.json() == {"delivered": True, "provider": "Telegram"}
