"""woncheon 신고 서비스 — 대상자 최소수집(주민번호) + PAID 전이 후 best-effort 신고.

암호화는 payouts.application.crypto(Fernet, SETTLEMENT_ENC_KEY)를 그대로 재사용한다 —
계좌번호 암호화와 같은 키 관리 패턴, 새 암호화 방식을 발명하지 않는다(CLAUDE.md 지시).
"""
import logging
from datetime import UTC, datetime
from uuid import UUID

from src.features.payouts.application.crypto import decrypt, encrypt
from src.features.woncheon.domain.models import (
    ReportResult,
    UnreportedPayoutView,
    WithholdingRepository,
    WoncheonReportingPort,
)
from src.shared.errors import ValidationError

logger = logging.getLogger(__name__)


class WoncheonReportingService:
    def __init__(
        self,
        repo: WithholdingRepository,
        port: WoncheonReportingPort,
        default_income_type_code: str | None,
    ):
        self.repo = repo
        self.port = port
        self.default_income_type_code = default_income_type_code

    async def register_subject(
        self, payout_id: UUID, resident_number: str, income_type_code: str | None = None
    ) -> None:
        """지급 대상자 최소수집 — bank_account(계좌등록)와 별개, 신고에 필요한 시점에만.

        income_type_code 미지정이면 설정 기본값(WONCHEON_DEFAULT_INCOME_TYPE_CODE) 사용.
        둘 다 없으면 세무사 판정 전 하드코딩을 피하기 위해 명시적으로 거부한다.
        """
        code = income_type_code or self.default_income_type_code
        if not code:
            raise ValidationError(
                "소득구분(income_type_code) 미설정 — WONCHEON_DEFAULT_INCOME_TYPE_CODE 또는 "
                "요청값이 필요해요(세무사 판정 전 임의값 금지)."
            )
        digits = (resident_number or "").replace("-", "").strip()
        if not digits.isdigit() or len(digits) != 13:
            raise ValidationError("주민등록번호 형식을 확인해 주세요.")
        await self.repo.upsert_subject(payout_id, encrypt(digits), code)

    async def report_paid(self, payout_id: UUID) -> ReportResult:
        """PAID 전이 후 호출 지점 — 데이터 미비·연동 실패는 예외 없이 ok=False 로 반환한다
        (payouts.PayoutReportHook 이 이 결과를 로그로만 남기고 지급 자체는 막지 않음).
        """
        subject = await self.repo.get_subject(payout_id)
        if subject is None:
            return ReportResult(ok=False, message="주민번호 미등록 — 신고 보류")

        gross = await self.repo.get_payout_gross(payout_id)
        if gross is None:
            return ReportResult(ok=False, message="payout을 찾을 수 없음")

        try:
            result = await self.port.report_payment(
                payout_id=payout_id,
                gross_amount=gross,
                income_type_code=subject.income_type_code,
                payee_resident_number=decrypt(subject.resident_no_enc),
            )
        except Exception as e:  # 설정 미비(WoncheonNotConfigured)·네트워크 실패 등 — best-effort
            logger.warning("woncheon 신고 실패: payout=%s error=%s", payout_id, e)
            return ReportResult(ok=False, message=str(e))

        if result.ok:
            await self.repo.mark_reported(payout_id, datetime.now(UTC))
        return result

    async def list_unreported(self) -> list[UnreportedPayoutView]:
        return await self.repo.list_unreported_paid()
