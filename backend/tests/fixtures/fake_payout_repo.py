"""인메모리 PayoutRepository(payouts 피처) — 서비스 단위 테스트용.

Protocol 구현 대상: src.features.payouts.domain.models.PayoutRepository
  (get_bank_account · upsert_bank_account · payable_summary · create_payout ·
   list_payouts · get_payout · list_by_status · transition)
"""
import uuid
from datetime import UTC, datetime
from uuid import UUID

from src.features.payouts.domain.models import (
    REQUESTED,
    BankAccountView,
    PayableSummary,
    PayoutView,
)


# ── Fake 리포지토리 ──────────────────────────────────
class FakePayoutRepository:
    def __init__(self) -> None:
        self.accounts: dict[UUID, BankAccountView] = {}
        self.account_no_enc: dict[UUID, str] = {}  # 서비스가 넘긴 암호문 검증용
        self.payables: dict[UUID, PayableSummary] = {}
        self.payouts: dict[UUID, PayoutView] = {}

    # ── 테스트 준비 헬퍼 ──────────────────────────────
    def seed_payable(self, author_id: UUID, summary: PayableSummary) -> None:
        self.payables[author_id] = summary

    def seed_payout(self, view: PayoutView) -> None:
        self.payouts[view.id] = view

    # ── 계좌 ──────────────────────────────────────────
    async def get_bank_account(self, account_id: UUID) -> BankAccountView | None:
        return self.accounts.get(account_id)

    async def upsert_bank_account(
        self, account_id: UUID, holder_name: str, bank: str, account_no_enc: str, account_no_masked: str
    ) -> BankAccountView:
        view = BankAccountView(id=uuid.uuid4(), holder_name=holder_name, bank=bank, account_no_masked=account_no_masked)
        self.accounts[account_id] = view
        self.account_no_enc[account_id] = account_no_enc
        return view

    # ── 출금 가능액 ───────────────────────────────────
    async def payable_summary(self, author_id: UUID) -> PayableSummary:
        return self.payables.get(author_id, PayableSummary(gross_amt=0, withholding_amt=0, net_amt=0, order_count=0))

    async def create_payout(self, author_id: UUID, account: BankAccountView) -> PayoutView | None:
        summary = self.payables.get(author_id)
        if summary is None or summary.order_count == 0:
            return None
        view = PayoutView(
            id=uuid.uuid4(), author_id=author_id, status=REQUESTED,
            gross_amt=summary.gross_amt, withholding_amt=summary.withholding_amt, net_amt=summary.net_amt,
            holder_name=account.holder_name, bank=account.bank, account_no_masked=account.account_no_masked,
            requested_at=datetime.now(UTC),
        )
        self.payouts[view.id] = view
        self.payables.pop(author_id, None)  # 정산분 소진(회수는 REJECTED 전이에서만 되돌림)
        return view

    # ── 조회 ──────────────────────────────────────────
    async def list_payouts(self, author_id: UUID) -> list[PayoutView]:
        rows = [p for p in self.payouts.values() if p.author_id == author_id]
        rows.sort(key=lambda p: p.requested_at, reverse=True)
        return rows

    async def get_payout(self, payout_id: UUID) -> PayoutView | None:
        return self.payouts.get(payout_id)

    async def list_by_status(self, status: str | None) -> list[PayoutView]:
        if status is None:
            return list(self.payouts.values())
        return [p for p in self.payouts.values() if p.status == status]

    # ── 운영자 상태 전이 ──────────────────────────────
    async def transition(
        self, payout_id, from_statuses, to_status, operator_id, now, memo=None
    ) -> bool:
        p = self.payouts.get(payout_id)
        if p is None or p.status not in from_statuses:
            return False
        p.status = to_status
        if memo is not None:
            p.memo = memo
        if to_status == "APPROVED":
            p.approved_at = now
        elif to_status == "PAID":
            p.paid_at = now
        return True
