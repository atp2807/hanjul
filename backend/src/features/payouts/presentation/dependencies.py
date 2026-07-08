"""payouts DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.infrastructure.payout_repo import SqlPayoutRepository
from src.features.woncheon.presentation.dependencies import build_payout_report_hook


def get_payout_service(session: AsyncSession = Depends(get_session)) -> PayoutService:
    # report_hook = woncheon 원천징수 신고 커넥터(lr-ac61f505) — best-effort, PAID 전이를
    # 막지 않는다. 설정(WONCHEON_API_KEY 등) 미주입 상태에선 훅이 조립은 되지만 실제 호출
    # 시점(mark_paid)에만 명시적으로 실패(로그)하고 지급은 그대로 유지된다.
    return PayoutService(SqlPayoutRepository(session), report_hook=build_payout_report_hook(session))
