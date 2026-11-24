from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import AUTH_COOKIE_NAME
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    AdminCreateUserRequest,
    AuthenticatedUser,
    ChangePasswordRequest,
    LoginRequest,
    ManagedUser,
    ManagedUserUpdateRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    UserProfile,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user: User) -> None:
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


def _get_current_account(request: Request, db: Session) -> User:
    account = db.scalar(select(User).where(User.email == request.state.user["email"]))
    if account is None or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive or unavailable")
    return account


def _require_administrator(request: Request, db: Session) -> User:
    account = _get_current_account(request, db)
    if account.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return account


def _profile(account: User) -> UserProfile:
    return UserProfile(email=account.email, display_name=account.display_name, role=account.role)


def _managed_user(account: User) -> ManagedUser:
    return ManagedUser(
        id=str(account.id),
        email=account.email,
        display_name=account.display_name,
        role=account.role,
        is_active=account.is_active,
        created_at=account.created_at,
    )


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

    _set_auth_cookie(response, user)
    return AuthenticatedUser(email=user.email, role=user.role)


@router.post("/register", response_model=AuthenticatedUser, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> AuthenticatedUser:
    if db.scalar(select(User.id).limit(1)) is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account registration is unavailable until an administrator is provisioned.",
        )
    email = str(payload.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role="viewer",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    _set_auth_cookie(response, user)
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
def current_user(request: Request, db: Session = Depends(get_db)) -> AuthenticatedUser:
    user = _get_current_account(request, db)
    return AuthenticatedUser(email=user.email, role=user.role)


@router.get("/profile", response_model=UserProfile)
def get_profile(request: Request, db: Session = Depends(get_db)) -> UserProfile:
    return _profile(_get_current_account(request, db))


@router.patch("/profile", response_model=UserProfile)
def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserProfile:
    user = _get_current_account(request, db)
    if "email" in payload.model_fields_set:
        email = str(payload.email).strip().lower() if payload.email is not None else user.email
        other_user = db.scalar(select(User.id).where(User.email == email, User.id != user.id))
        if other_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
        user.email = email
    if "display_name" in payload.model_fields_set and payload.display_name is not None:
        user.display_name = payload.display_name
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    _set_auth_cookie(response, user)
    return _profile(user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user = _get_current_account(request, db)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New password must be different")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    _set_auth_cookie(response, user)
    return {"password_changed": True}


@router.get("/users", response_model=list[ManagedUser])
def list_users(request: Request, db: Session = Depends(get_db)) -> list[ManagedUser]:
    _require_administrator(request, db)
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.email)).all()
    return [_managed_user(user) for user in users]


@router.post("/users", response_model=ManagedUser, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ManagedUser:
    _require_administrator(request, db)
    email = str(payload.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    return _managed_user(user)


@router.patch("/users/{user_id}", response_model=ManagedUser)
def update_user(
    user_id: UUID,
    payload: ManagedUserUpdateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> ManagedUser:
    administrator = _require_administrator(request, db)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == administrator.id and (
        payload.role == "viewer" or payload.is_active is False
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot disable or demote your own account")

    if payload.email is not None:
        email = str(payload.email).strip().lower()
        other_user = db.scalar(select(User.id).where(User.email == email, User.id != user.id))
        if other_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
        user.email = email
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    next_role = payload.role if payload.role is not None else user.role
    next_active = payload.is_active if payload.is_active is not None else user.is_active
    if user.role == "administrator" and user.is_active and (next_role != "administrator" or not next_active):
        active_admins = db.scalar(
            select(func.count(User.id)).where(User.role == "administrator", User.is_active.is_(True))
        ) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The last active administrator cannot be disabled or demoted")
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    if user.id == administrator.id:
        _set_auth_cookie(response, user)
    return _managed_user(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    administrator = _require_administrator(request, db)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == administrator.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot delete your own account")
    if user.role == "administrator" and user.is_active:
        active_admins = db.scalar(
            select(func.count(User.id)).where(User.role == "administrator", User.is_active.is_(True))
        ) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The last active administrator cannot be deleted")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
