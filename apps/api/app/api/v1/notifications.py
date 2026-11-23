from fastapi import APIRouter, HTTPException
import httpx

from app.core.config import get_settings

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/status")
def notification_status() -> dict:
    settings = get_settings()
    configured = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    chat_id = settings.telegram_chat_id
    masked_chat_id = chat_id if len(chat_id) <= 4 else f"…{chat_id[-4:]}"
    return {
        "configured": configured,
        "chat_id": masked_chat_id if configured else "",
        "provider": "Telegram",
    }


@router.post("/test")
def send_test_notification() -> dict:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise HTTPException(status_code=400, detail="Telegram is not configured")

    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={
                "chat_id": settings.telegram_chat_id,
                "text": "Forex Intelligence test notification",
                "disable_notification": False,
            },
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach Telegram") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Telegram rejected the test notification")
    return {"delivered": True, "provider": "Telegram"}
