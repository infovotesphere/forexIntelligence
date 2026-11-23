from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AUTH_COOKIE_NAME
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthenticatedUser)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthenticatedUser:
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        if db.scalar(select(User.id).limit(1)) is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No user is provisioned. Configure BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, then run the bootstrap command.",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    settings = get_settings()
    token = create_access_token(user.email, user.role)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.environment.lower() not in {"development", "test"},
        samesite="lax",
        path="/",
    )
    return AuthenticatedUser(email=user.email, role=user.role)


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    settings = get_settings()
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=settings.environment.lower() not in {"development", "test"},
        samesite="lax",
        path="/",
    )
    return {"logged_out": True}


@router.get("/me", response_model=AuthenticatedUser)
def current_user(request: Request) -> AuthenticatedUser:
    user = request.state.user
    return AuthenticatedUser(email=user["email"], role=user["role"])
