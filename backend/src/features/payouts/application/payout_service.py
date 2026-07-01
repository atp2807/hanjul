"""payouts 서비스 — 작가(계좌·출금신청) + 운영자(승인·지급·반려)."""
from datetime import datetime, timezone
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
    PayoutRepository,
    PayoutView,
)
from src.shared.errors import ValidationError


class PayoutService:
    def __init__(self, repo: PayoutRepository):
        self.repo = repo

    # ── 작가: 계좌 ────────────────────────────────────
    async def get_bank_account(self, account_id: UUID) -> BankAccountView | None:
        return await self.repo.get_bank_account(account_id)

    async def set_bank_account(
        self, account_id: UUID, holder_name: str, bank_cd: str, account_no: str
    ) -> BankAccountView:
        holder_name = (holder_name or "").strip()
        bank_cd = (bank_cd or "").strip()
        digits = (account_no or "").replace("-", "").replace(" ", "")
        if not holder_name or not bank_cd:
            raise ValidationError("예금주·은행은 필수예요")
        if not digits.isdigit() or not (6 <= len(digits) <= 20):
            raise ValidationError("계좌번호를 확인해 주세요")
        return await self.repo.upsert_bank_account(
            account_id, holder_name, bank_cd, encrypt(digits), mask_account(digits)
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

    # ── 운영자 ────────────────────────────────────────
    async def list_for_ops(self, status: str | None = REQUESTED) -> list[PayoutView]:
        return await self.repo.list_by_status(status)

    async def _require(self, payout_id: UUID) -> PayoutView:
        p = await self.repo.get_payout(payout_id)
        if p is None:
            raise PayoutNotFound()
        return p

    async def approve(self, payout_id: UUID, operator_id: UUID) -> None:
        p = await self._require(payout_id)
        if p.status_cd != REQUESTED:
            raise InvalidPayoutState()
        await self.repo.set_status(payout_id, APPROVED, operator_id, self._now())

    async def mark_paid(self, payout_id: UUID, operator_id: UUID, memo: str | None = None) -> None:
        """실이체 완료 후 지급확정 (이체 자체는 운영자가 수동)."""
        p = await self._require(payout_id)
        if p.status_cd != APPROVED:
            raise InvalidPayoutState()
        await self.repo.set_status(payout_id, PAID, operator_id, self._now(), memo)

    async def reject(self, payout_id: UUID, operator_id: UUID, memo: str | None = None) -> None:
        p = await self._require(payout_id)
        if p.status_cd not in (REQUESTED, APPROVED):
            raise InvalidPayoutState()
        # 정산분 회수 → 다시 출금 가능
        await self.repo.unlink_settlements(payout_id)
        await self.repo.set_status(payout_id, REJECTED, operator_id, self._now(), memo)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
