"""potato API — 운영자 인증 (별도 영역, prefix /api/potato).

surface 는 별도 앱(potato.hanjul.io). 공개 가입 없음 — 계정은 서버 CLI 로만 생성.
"""
from fastapi import APIRouter, Depends

from src.features.potato.application.auth_service import PotatoAuthService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    get_current_operator,
    get_potato_auth_service,
)
from src.features.potato.presentation.schemas import (
    LoginRequest,
    OperatorResponse,
    TokenResponse,
)

router = APIRouter(prefix="/potato", tags=["potato"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, svc: PotatoAuthService = Depends(get_potato_auth_service)
) -> TokenResponse:
    # InvalidCredentials 401·OperatorInactive 403 → 중앙 핸들러
    token, role = await svc.login(body.email, body.password)
    return TokenResponse(token=token, role=role)


@router.get("/auth/me", response_model=OperatorResponse)
async def me(
    principal: OperatorPrincipal = Depends(get_current_operator),
    svc: PotatoAuthService = Depends(get_potato_auth_service),
) -> OperatorResponse:
    # OperatorNotFound 404 → 중앙 핸들러 (get_current_operator 401은 표현층 인증 판단이라 유지)
    operator = await svc.get_operator(principal.id)
    return OperatorResponse.model_validate(operator)
