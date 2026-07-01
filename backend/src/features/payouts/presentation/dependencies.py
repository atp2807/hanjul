"""payouts DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.infrastructure.payout_repo import SqlPayoutRepository


def get_payout_service(session: AsyncSession = Depends(get_session)) -> PayoutService:
    return PayoutService(SqlPayoutRepository(session))
