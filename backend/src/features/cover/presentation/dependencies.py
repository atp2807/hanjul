"""cover 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.cover.application.cover_service import CoverService
from src.features.cover.infrastructure.cover_repo import SqlCoverRepository
from src.features.cover.infrastructure.novelpotato_generator import NovelpotatoCoverGenerator


def get_cover_service(session: AsyncSession = Depends(get_session)) -> CoverService:
    return CoverService(
        repo=SqlCoverRepository(session),
        generator=NovelpotatoCoverGenerator(settings.COVER_API_URL, settings.COVER_API_KEY),
    )
