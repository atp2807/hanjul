"""accounts 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.infrastructure.account_repo import SqlAccountRepository


def get_account_service(session: AsyncSession = Depends(get_session)) -> AccountService:
    return AccountService(SqlAccountRepository(session))
