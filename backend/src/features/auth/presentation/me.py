"""현재 로그인 계정 — GET /api/me."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_current_account
from src.features.auth.presentation.schemas import AccountResponse

router = APIRouter(tags=["account"])


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
    )
