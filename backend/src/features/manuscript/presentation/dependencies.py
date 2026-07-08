"""manuscript DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.manuscript.application.manuscript_service import ManuscriptService
from src.features.manuscript.infrastructure.manuscript_repo import SqlManuscriptRepository


def get_manuscript_service(session: AsyncSession = Depends(get_session)) -> ManuscriptService:
    return ManuscriptService(SqlManuscriptRepository(session))
