"""auth API 엔드포인트 — 소셜 로그인 (브라우저 리다이렉트 플로우)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from src.config.settings import settings
from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import UnknownProvider
from src.features.auth.presentation.dependencies import get_auth_service
from src.features.auth.presentation.schemas import LoginUrlResponse

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


@router.get("/{provider}/callback")
async def callback(
    provider: str, code: str, service: AuthService = Depends(get_auth_service)
) -> RedirectResponse:
    """Google 콜백 처리 → JWT 발급 → 프론트로 리다이렉트.

    토큰은 URL fragment(#)로 전달 — 서버 로그·Referer 헤더에 남지 않는다.
    프론트 /auth/callback 페이지가 location.hash 에서 읽어 저장한다.
    """
    try:
        result = await service.complete_login(provider, code)
    except UnknownProvider:
        raise HTTPException(status_code=400, detail="unknown provider")
    fragment = f"token={result.token}&isNew={'1' if result.is_new else '0'}"
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback#{fragment}", status_code=302)
