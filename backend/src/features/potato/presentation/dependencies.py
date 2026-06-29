"""potato 표현 레이어 DI — 고객(auth)과 분리된 운영자 인증 합성 루트."""
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.potato.application.audit import AuditService
from src.features.potato.application.auth_service import PotatoAuthService
from src.features.potato.application.token import PotatoTokenIssuer
from src.features.potato.domain.models import DEVELOPER, OperatorPrincipal
from src.features.potato.infrastructure.audit_repo import SqlAuditRepository
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository


def potato_token_issuer() -> PotatoTokenIssuer:
    return PotatoTokenIssuer(
        settings.POTATO_JWT_SECRET_KEY, settings.JWT_ALG, settings.POTATO_JWT_TTL_HOURS
    )


def get_potato_auth_service(session: AsyncSession = Depends(get_session)) -> PotatoAuthService:
    return PotatoAuthService(SqlOperatorRepository(session), potato_token_issuer())


def get_audit_service(session: AsyncSession = Depends(get_session)) -> AuditService:
    return AuditService(SqlAuditRepository(session))


_bearer = HTTPBearer(auto_error=False)


def get_current_operator(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> OperatorPrincipal:
    """potato 토큰 필수. 고객 토큰(다른 시크릿·aud 없음)은 검증 실패 → 401."""
    if creds is None:
        raise HTTPException(status_code=401, detail="operator authentication required")
    try:
        payload = potato_token_issuer().verify(creds.credentials)
        return OperatorPrincipal(id=UUID(payload["sub"]), role_cd=payload.get("role", "OPERATOR"))
    except Exception:
        raise HTTPException(status_code=401, detail="operator authentication required")


def require_developer(
    principal: OperatorPrincipal = Depends(get_current_operator),
) -> OperatorPrincipal:
    """개발자 전용(시스템/엔진 메뉴). 일반 운영자는 403."""
    if principal.role_cd != DEVELOPER:
        raise HTTPException(status_code=403, detail="developer only")
    return principal
