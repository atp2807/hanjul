"""billing 표현 레이어 DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.infrastructure.account_repo import SqlAccountRepository
from src.features.billing.application.order_service import OrderService
from src.features.billing.infrastructure.book_pricing import SqlBookPricing
from src.features.billing.infrastructure.demo_gateway import DemoPaymentGateway
from src.features.billing.infrastructure.order_repo import SqlOrderRepository
from src.features.billing.infrastructure.toss_gateway import TossPaymentGateway
from src.features.email.presentation.dependencies import build_order_email_hook


def _gateway():
    # 데모 모드면 검증 없이 성공, 아니면 실 토스 승인 (운영은 PAYMENT_DEMO=False)
    if settings.PAYMENT_DEMO:
        return DemoPaymentGateway()
    return TossPaymentGateway(settings.TOSS_TEST_SECRET_KEY, settings.TOSS_PAYMENT_MOCK_MODE)


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    pricing = SqlBookPricing(session)  # get_content_rating도 겸함(연령 게이트, dc-daeb0d3d)
    return OrderService(
        repo=SqlOrderRepository(session),
        gateway=_gateway(),
        pricing=pricing,
        rating_lookup=pricing,
        account_tier=AccountService(SqlAccountRepository(session)),
        # 주문확인 메일 best-effort 훅(email 피처) — woncheon build_payout_report_hook과 동형 패턴.
        email_hook=build_order_email_hook(session),
    )
