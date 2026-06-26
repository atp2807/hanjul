"""campaigns 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.campaigns.application.campaign_service import CampaignService
from src.features.campaigns.infrastructure.campaign_repo import SqlCampaignRepository


def get_campaign_service(session: AsyncSession = Depends(get_session)) -> CampaignService:
    return CampaignService(SqlCampaignRepository(session))
