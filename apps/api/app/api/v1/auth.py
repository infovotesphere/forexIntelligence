from fastapi import APIRouter, HTTPException, status
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    # Demo/phase-1 identity. Broker and user database seeding are completed in later phases.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="User provisioning is not enabled yet")
