"""payouts.domain.models.PayoutReportHook 구현 — PAID 전이 시 best-effort woncheon 신고.

payouts 피처는 이 클래스의 존재를 모른다(Protocol만 안다) — DI(payouts/presentation/
dependencies.py)가 이 구현을 주입한다. 여기서 예외를 삼키지 않아도 되는 건
WoncheonReportingService.report_paid 가 이미 내부에서 실패를 ReportResult(ok=False)로
변환해 반환하기 때문(예외를 던지지 않음) — 그래도 PayoutService.mark_paid 쪽에도
방어적 try/except가 있어 이중 방어(지급을 절대 막지 않는다는 게 핵심 불변식).
"""
import logging
from uuid import UUID

from src.features.woncheon.application.reporting_service import WoncheonReportingService

logger = logging.getLogger(__name__)


class WoncheonPayoutReportHook:
    def __init__(self, service: WoncheonReportingService):
        self.service = service

    async def on_paid(self, payout_id: UUID) -> None:
        result = await self.service.report_paid(payout_id)
        if not result.ok:
            logger.warning("woncheon 신고 보류/실패: payout=%s reason=%s", payout_id, result.message)
