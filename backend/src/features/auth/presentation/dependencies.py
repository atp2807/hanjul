"""auth 표현 레이어 DI 합성 루트."""
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.auth.application.auth_service import AuthService
from src.features.auth.application.token import JwtTokenIssuer
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.infrastructure.providers import build_providers
from src.shared.errors import UnauthorizedError


def token_issuer() -> JwtTokenIssuer:
    return JwtTokenIssuer(settings.JWT_SECRET_KEY, settings.JWT_ALG, settings.JWT_TTL_HOURS)


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(
        repo=SqlAccountRepository(session),
        providers=build_providers(settings),
        token_issuer=token_issuer(),
    )


_bearer = HTTPBearer(auto_error=False)


def _principal_from(creds: HTTPAuthorizationCredentials | None) -> AccountPrincipal | None:
    if creds is None:
        return None
    try:
        payload = token_issuer().verify(creds.credentials)
        return AccountPrincipal(id=UUID(payload["sub"]), role=payload.get("role", "READER"))
    except Exception:
        return None


def get_current_account(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AccountPrincipal:
    """Authorization: Bearer 필수. 없거나 유효하지 않으면 401."""
    principal = _principal_from(creds)
    if principal is None:
        raise UnauthorizedError("authentication required")
    return principal


def get_current_account_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AccountPrincipal | None:
    """로그인 선택 (미리보기 게이팅 등) — 토큰 없거나 무효면 None."""
    return _principal_from(creds)
