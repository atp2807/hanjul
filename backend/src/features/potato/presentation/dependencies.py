"""potato 표현 레이어 DI — 고객(auth)과 분리된 운영자 인증 합성 루트."""
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.potato.application.audit import AuditService
from src.features.potato.application.auth_service import PotatoAuthService
from src.features.potato.application.dashboard import DashboardService
from src.features.potato.application.token import PotatoTokenIssuer
from src.features.potato.domain.models import DEVELOPER, OperatorPrincipal
from src.features.potato.infrastructure.audit_repo import SqlAuditRepository
from src.features.potato.infrastructure.operator_repo import SqlOperatorRepository
from src.features.potato.infrastructure.stats_repo import SqlStatsRepository


def potato_token_issuer() -> PotatoTokenIssuer:
    return PotatoTokenIssuer(
        settings.POTATO_JWT_SECRET_KEY, settings.JWT_ALG, settings.POTATO_JWT_TTL_HOURS
    )


def get_potato_auth_service(session: AsyncSession = Depends(get_session)) -> PotatoAuthService:
    return PotatoAuthService(SqlOperatorRepository(session), potato_token_issuer())


def get_audit_service(session: AsyncSession = Depends(get_session)) -> AuditService:
    return AuditService(SqlAuditRepository(session))


def get_dashboard_service(session: AsyncSession = Depends(get_session)) -> DashboardService:
    return DashboardService(SqlStatsRepository(session))


_LOOPBACK = {"127.0.0.1", "::1"}


def _effective_ip(request: Request) -> str:
    """진짜 클라이언트 IP.

    1순위 CF-Connecting-IP — Cloudflare가 세팅, CF 통과 시 위조 불가(권위).
    2순위 X-Forwarded-For의 **마지막** 항목 — nginx가 append한 실제 TCP peer.
      (앞쪽은 클라가 위조 가능하므로 신뢰하지 않음. origin 직접접근 방어.)
    3순위 request.client — nginx 미경유(로컬) 경우뿐.
    """
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else ""


def require_allowed_ip(request: Request) -> None:
    """운영자 영역 IP 화이트리스트. 비면 무제한(dev), 로컬(loopback)은 항상 허용.

    운영(Cloudflare 프록시)에선 effective IP=CF-Connecting-IP 라 loopback 으로 안 떨어짐
    → 화이트리스트가 실제로 강제됨. 직접 origin 접근은 XFF/허용목록 불일치로 403.
    """
    allowed = settings.potato_allowed_ip_list
    if not allowed:
        return
    ip = _effective_ip(request)
    if ip in _LOOPBACK:
        return
    if ip not in allowed:
        raise HTTPException(status_code=403, detail="forbidden")


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
