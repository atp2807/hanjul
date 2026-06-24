"""현재 로그인 계정 — GET /api/me, PUT /api/me/profile."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_current_account
from src.features.auth.presentation.schemas import AccountResponse

router = APIRouter(tags=["account"])


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    bio: str | None = Field(default=None, max_length=1000)


@router.get("/me", response_model=AccountResponse)
async def me(
    principal: AccountPrincipal = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> AccountResponse:
    account = await SqlAccountRepository(session).get_account(principal.id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    return AccountResponse(
        id=account.id,
        email=account.email,
        display_name=account.display_name,
        role_cd=account.role_cd,
        bio=account.bio,
    )


@router.put("/me/profile", status_code=204)
async def update_profile(
    body: UpdateProfileRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> None:
    """작가 소개(bio) 수정."""
    await SqlAccountRepository(session).update_bio(principal.id, body.bio)
