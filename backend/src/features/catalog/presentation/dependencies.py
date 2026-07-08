"""catalog 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.infrastructure.account_repo import SqlAccountRepository
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository


def get_catalog_service(session: AsyncSession = Depends(get_session)) -> CatalogService:
    return CatalogService(
        SqlCatalogRepository(session),
        account_tier=AccountService(SqlAccountRepository(session)),
    )
