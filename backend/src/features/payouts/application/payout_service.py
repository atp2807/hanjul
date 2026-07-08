"""payouts 서비스 — 작가(계좌·출금신청) + 운영자(승인·지급·반려)."""
import logging
from datetime import UTC, date, datetime
from uuid import UUID

from src.features.payouts.application.crypto import encrypt, mask_account
from src.features.payouts.domain.models import (
    APPROVED,
    PAID,
    REJECTED,
    REQUESTED,
    BankAccountView,
    InvalidPayoutState,
    NoBankAccount,
    NothingToPayout,
    PayableSummary,
    PayoutNotFound,
    PayoutReportHook,
    PayoutRepository,
    PayoutView,
)
from src.shared.errors import ValidationError

logger = logging.getLogger(__name__)


class PayoutService:
    def __init__(self, repo: PayoutRepository, report_hook: PayoutReportHook | None = None):
        self.repo = repo
        self.report_hook = report_hook

    # ── 작가: 계좌 ────────────────────────────────────
    async def get_bank_account(self, account_id: UUID) -> BankAccountView | None:
        return await self.repo.get_bank_account(account_id)

    async def set_bank_account(
        self, account_id: UUID, holder_name: str, bank: str, account_no: str
    ) -> BankAccountView:
        holder_name = (holder_name or "").strip()
        bank = (bank or "").strip()
        digits = (account_no or "").replace("-", "").replace(" ", "")
        if not holder_name or not bank:
            raise ValidationError("예금주·은행은 필수예요")
        if not digits.isdigit() or not (6 <= len(digits) <= 20):
            raise ValidationError("계좌번호를 확인해 주세요")
        return await self.repo.upsert_bank_account(
            account_id, holder_name, bank, encrypt(digits), mask_account(digits)
        )

    # ── 작가: 출금 ────────────────────────────────────
    async def payable(self, author_id: UUID) -> PayableSummary:
        return await self.repo.payable_summary(author_id)

    async def request_payout(self, author_id: UUID) -> PayoutView:
        account = await self.repo.get_bank_account(author_id)
        if account is None:
            raise NoBankAccount()
        payout = await self.repo.create_payout(author_id, account)
        if payout is None:
            raise NothingToPayout()
        return payout

    async def list_payouts(self, author_id: UUID) -> list[PayoutView]:
        return await self.repo.list_payouts(author_id)

    # ── 매주 수요일 고정 정산 배치(lr-a0a8bda9) ───────
    async def run_weekly_settlement(self, run_date: date) -> int:
        """환불세이프 미지급 정산이 있는 작가 전부를 훑어 payout(REQUESTED)을 생성한다.

        run_date 당 최대 1회만 실제 실행(claim_settlement_run 멱등 가드) — 스케줄러가
        같은 수요일에 여러 번 불러도(30초 주기) 2회차부터는 즉시 0을 반환한다. 계좌
        미등록 작가는 스킵(다음 수요일 재시도) — 자기명의 신청(POST /me/payouts)과
        환불세이프 게이트(create_payout/_unpaid_stmt)를 그대로 공유하므로 이중지급 위험 없음.
        """
        if not await self.repo.claim_settlement_run(run_date):
            return 0
        count = 0
        for author_id in await self.repo.authors_with_payable():
            account = await self.repo.get_bank_account(author_id)
            if account is None:
                continue
            payout = await self.repo.create_payout(author_id, account)
            if payout is not None:
                count += 1
        await self.repo.record_settlement_run_count(run_date, count)
        return count

    # ── 운영자 ────────────────────────────────────────
    async def list_for_ops(self, status: str | None = REQUESTED) -> list[PayoutView]:
        return await self.repo.list_by_status(status)

    async def _require(self, payout_id: UUID) -> PayoutView:
        p = await self.repo.get_payout(payout_id)
        if p is None:
            raise PayoutNotFound()
        return p

    async def get(self, payout_id: UUID) -> PayoutView:
        """상태전이 직후 스냅샷 재조회 — potato 출금상태 안내메일 등 부가 훅용."""
        return await self._require(payout_id)

    async def approve(self, payout_id: UUID, operator_id: UUID) -> None:
        await self._require(payout_id)  # 없으면 404
        if not await self.repo.transition(payout_id, (REQUESTED,), APPROVED, operator_id, self._now()):
            raise InvalidPayoutState()

    async def mark_paid(self, payout_id: UUID, operator_id: UUID, memo: str | None = None) -> None:
        """실이체 완료 후 지급확정 (이체 자체는 운영자가 수동).

        report_hook(예: woncheon 원천징수 신고 커넥터, lr-ac61f505)은 best-effort —
        실패해도 PAID 전이는 이미 확정된 채로 유지한다. 실패는 로그만 남기고 재시도는
        이 메서드 범위 밖(수동 재시도 스크립트 — scripts/woncheon_retry_report.py).
        """
        await self._require(payout_id)
        if not await self.repo.transition(payout_id, (APPROVED,), PAID, operator_id, self._now(), memo):
            raise InvalidPayoutState()
        if self.report_hook is not None:
            try:
                await self.report_hook.on_paid(payout_id)
            except Exception:
                logger.exception(
                    "payout %s report_hook 실패 — PAID 상태는 유지, 신고는 미완(재시도 가능)", payout_id
                )

    async def reject(self, payout_id: UUID, operator_id: UUID, memo: str | None = None) -> None:
        """반려 — 정산분 회수(다시 출금 가능)까지 repo가 한 트랜잭션으로 처리."""
        await self._require(payout_id)
        if not await self.repo.transition(payout_id, (REQUESTED, APPROVED), REJECTED, operator_id, self._now(), memo):
            raise InvalidPayoutState()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
