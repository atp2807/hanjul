"""auth API 엔드포인트 — 소셜 로그인."""
from fastapi import APIRouter, Depends, HTTPException

from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import UnknownProvider
from src.features.auth.presentation.dependencies import get_auth_service
from src.features.auth.presentation.schemas import (
    AccountResponse,
    AuthTokenResponse,
    LoginUrlResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{provider}/login", response_model=LoginUrlResponse)
async def login(
    provider: str, state: str = "", service: AuthService = Depends(get_auth_service)
) -> LoginUrlResponse:
    try:
        url = service.login_url(provider, state)
    except UnknownProvider:
        raise HTTPException(status_code=400, detail="unknown provider")
    return LoginUrlResponse(authorization_url=url)


@router.get("/{provider}/callback", response_model=AuthTokenResponse)
async def callback(
    provider: str, code: str, service: AuthService = Depends(get_auth_service)
) -> AuthTokenResponse:
    try:
        result = await service.complete_login(provider, code)
    except UnknownProvider:
        raise HTTPException(status_code=400, detail="unknown provider")
    return AuthTokenResponse(
        token=result.token,
        is_new=result.is_new,
        account=AccountResponse(
            id=result.account.id,
            email=result.account.email,
            display_name=result.account.display_name,
            role_cd=result.account.role_cd,
        ),
    )
