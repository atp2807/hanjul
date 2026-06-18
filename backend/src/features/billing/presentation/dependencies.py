"""billing 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.billing.application.order_service import OrderService
from src.features.billing.infrastructure.order_repo import SqlOrderRepository
from src.features.billing.infrastructure.portone_gateway import PortonePaymentGateway


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(
        repo=SqlOrderRepository(session),
        gateway=PortonePaymentGateway(settings.PORTONE_API_SECRET),
    )
