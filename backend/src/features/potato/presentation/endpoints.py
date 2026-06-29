"""potato API — 운영자 인증 (별도 영역, prefix /api/potato).

surface 는 별도 앱(potato.hanjul.io). 공개 가입 없음 — 계정은 서버 CLI 로만 생성.
"""
from fastapi import APIRouter, Depends, HTTPException

from src.features.potato.application.auth_service import PotatoAuthService
from src.features.potato.domain.models import (
    InvalidCredentials,
    OperatorInactive,
    OperatorNotFound,
    OperatorPrincipal,
)
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
    try:
        token, role_cd = await svc.login(body.email, body.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="invalid credentials")
    except OperatorInactive:
        raise HTTPException(status_code=403, detail="operator inactive")
    return TokenResponse(token=token, role_cd=role_cd)


@router.get("/auth/me", response_model=OperatorResponse)
async def me(
    principal: OperatorPrincipal = Depends(get_current_operator),
    svc: PotatoAuthService = Depends(get_potato_auth_service),
) -> OperatorResponse:
    try:
        operator = await svc.get_operator(principal.id)
    except OperatorNotFound:
        raise HTTPException(status_code=404, detail="operator not found")
    return OperatorResponse.model_validate(operator)
