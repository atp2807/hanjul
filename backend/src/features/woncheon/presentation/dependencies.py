"""woncheon 커넥터 DI — potato 조회/등록용 서비스 + payouts PAID 훅 wiring.

이 파일이 woncheon 피처의 composition root. payouts 는 PayoutReportHook(Protocol)만
알고, 여기서 그 구현(WoncheonPayoutReportHook)을 조립해 payouts DI 에 건네준다.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.config.settings import settings as _settings
from src.features.payouts.domain.models import PayoutReportHook
from src.features.woncheon.application.reporting_service import WoncheonReportingService
from src.features.woncheon.infrastructure.payout_hook import WoncheonPayoutReportHook
from src.features.woncheon.infrastructure.withholding_repo import SqlWithholdingRepository
from src.features.woncheon.infrastructure.woncheon_adapter import build_woncheon_adapter


def get_woncheon_service(session: AsyncSession = Depends(get_session)) -> WoncheonReportingService:
    repo = SqlWithholdingRepository(session)
    port = build_woncheon_adapter(_settings)
    return WoncheonReportingService(repo, port, _settings.WONCHEON_DEFAULT_INCOME_TYPE_CODE or None)


def build_payout_report_hook(session: AsyncSession) -> PayoutReportHook:
    """payouts/presentation/dependencies.py(get_payout_service)에서 호출 — FastAPI Depends
    캐시 밖에서 같은 session 으로 서비스를 조립하기 위해 함수 형태로 노출."""
    return WoncheonPayoutReportHook(get_woncheon_service(session))
