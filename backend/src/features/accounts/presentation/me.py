"""현재 로그인 계정(유저) — GET /api/me, PUT /api/me/profile.

인증(누구인지)은 auth 의 get_current_account 가, 유저 데이터(프로필)는 accounts 가.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.features.accounts.application.account_service import AccountService
from src.features.accounts.domain.models import AccountNotFound
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.accounts.presentation.schemas import AccountResponse
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account

router = APIRouter(tags=["account"])


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    bio: str | None = Field(default=None, max_length=1000)


@router.get("/me", response_model=AccountResponse)
async def me(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> AccountResponse:
    try:
        acc = await svc.get_profile(principal.id)
    except AccountNotFound:
        raise HTTPException(status_code=404, detail="account not found")
    return AccountResponse.model_validate(acc)


@router.put("/me/profile", status_code=204)
async def update_profile(
    body: UpdateProfileRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> None:
    """작가 소개(bio) 수정."""
    await svc.update_bio(principal.id, body.bio)


@router.get("/me/export")
async def export_my_data(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> dict:
    """개인정보 열람/다운로드 (개인정보보호법 §35 열람권).

    구매·정산 내역은 각각 /me/library, /me/sales 로 조회.
    """
    try:
        acc = await svc.get_profile(principal.id)
    except AccountNotFound:
        raise HTTPException(status_code=404, detail="account not found")
    return {"account": AccountResponse.model_validate(acc).model_dump(by_alias=True)}


@router.delete("/me", status_code=204)
async def withdraw(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> None:
    """회원탈퇴 — 개인정보 익명화 + 소셜 연결 삭제.

    주문·정산 기록은 관련 법령(전자상거래법 5년)에 따라 계정 행을 익명 상태로 보존.
    """
    try:
        await svc.withdraw(principal.id)
    except AccountNotFound:
        raise HTTPException(status_code=404, detail="account not found")
