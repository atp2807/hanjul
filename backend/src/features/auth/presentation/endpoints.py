"""auth API 엔드포인트 — 소셜 로그인 (브라우저 리다이렉트 플로우)."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from src.config.settings import settings
from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import OAuthExchangeError, SocialProfile
from src.features.auth.presentation.dependencies import get_auth_service
from src.features.auth.presentation.schemas import LoginUrlResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app")


def _front_redirect(fragment: str) -> RedirectResponse:
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback#{fragment}", status_code=302)


@router.get("/{provider}/login", response_model=LoginUrlResponse)
async def login(
    provider: str, state: str = "", service: AuthService = Depends(get_auth_service)
) -> LoginUrlResponse:
    # UnknownProvider 400 → 중앙 핸들러
    url = service.login_url(provider, state)
    return LoginUrlResponse(authorization_url=url)


@router.get("/test-login")
async def test_login(
    email: str, name: str = "테스트작가", service: AuthService = Depends(get_auth_service)
) -> RedirectResponse:
    """E2E/로컬 전용 로그인 우회 — Google 콜백과 동일하게 토큰을 프론트로 전달.

    settings.E2E_LOGIN_ENABLED 가 True 일 때만 동작. 운영 기본값은 차단(404, fail-closed).
    경로는 1세그먼트라 /{provider}/login·/{provider}/callback 과 충돌하지 않는다.
    """
    if not settings.E2E_LOGIN_ENABLED:
        raise HTTPException(status_code=404, detail="not found")
    profile = SocialProfile("GOOGLE", f"e2e:{email}", email, name)
    result = await service.login_with_profile(profile)
    return _front_redirect(f"token={result.token}&isNew={'1' if result.is_new else '0'}")


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str | None = None,
    error: str | None = None,
    service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Google 콜백 처리 → JWT 발급 → 프론트로 리다이렉트.

    토큰은 URL fragment(#)로 전달 — 서버 로그·Referer 헤더에 남지 않는다.
    실패(사용자 취소·교환 실패)는 500/422 대신 프론트로 #error= 전달해 안내.
    """
    if error or not code:
        # 사용자가 동의 취소(access_denied) 또는 code 없음 → 422 대신 안내 리다이렉트
        return _front_redirect(f"error={error or 'no_code'}")
    try:
        result = await service.complete_login(provider, code)
    except OAuthExchangeError as e:
        # OAuth 교환 실패는 HTTP 에러가 아니라 프론트 안내 리다이렉트(#error=)로 변환 — 표현층 유지.
        logger.warning("OAuth 교환 실패 provider=%s: %s", provider, e.detail)  # redirect_uri_mismatch 등
        return _front_redirect("error=auth_failed")
    # UnknownProvider 400 은 도메인 예외 → 중앙 핸들러가 매핑.
    return _front_redirect(f"token={result.token}&isNew={'1' if result.is_new else '0'}")
