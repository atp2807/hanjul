"""payouts 도메인 — 작가 출금계좌 + 출금 배치.

흐름: 계좌 등록 → 미지급 정산분 집계(출금 가능액) → 출금 신청(payout, REQUESTED)
     → 운영자 승인(APPROVED) → 실이체 후 지급완료(PAID). 반려(REJECTED)면 정산분 회수.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

# payout 상태기계
REQUESTED = "REQUESTED"
APPROVED = "APPROVED"
PAID = "PAID"
REJECTED = "REJECTED"


@dataclass
class BankAccountView:
    id: UUID
    holder_name: str
    bank_cd: str
    account_no_masked: str


@dataclass
class PayoutView:
    id: UUID
    author_id: UUID
    status_cd: str
    gross_amt: int
    withholding_amt: int
    net_amt: int
    holder_name: str | None
    bank_cd: str | None
    account_no_masked: str | None
    requested_at: datetime
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    memo: str | None = None


@dataclass
class PayableSummary:
    """현재 출금 가능한 미지급 정산 집계."""
    gross_amt: int
    withholding_amt: int
    net_amt: int
    order_count: int


class NoBankAccount(Exception):
    """출금계좌 미등록 상태에서 출금 신청."""


class NothingToPayout(Exception):
    """출금 가능 잔액 없음."""


class PayoutNotFound(Exception):
    ...


class InvalidPayoutState(Exception):
    """상태기계 위반 (예: 이미 지급된 건 재승인)."""


class PayoutRepository(Protocol):
    # 계좌
    async def get_bank_account(self, account_id: UUID) -> BankAccountView | None: ...
    async def upsert_bank_account(
        self, account_id: UUID, holder_name: str, bank_cd: str, account_no_enc: str, account_no_masked: str
    ) -> BankAccountView: ...

    # 출금 가능액(미지급 정산 집계)
    async def payable_summary(self, author_id: UUID) -> PayableSummary: ...

    # 출금 신청 — 미지급 정산분을 payout 으로 묶고 스냅샷 저장. 없으면 None.
    async def create_payout(self, author_id: UUID, account: BankAccountView) -> PayoutView | None: ...

    # 조회
    async def list_payouts(self, author_id: UUID) -> list[PayoutView]: ...
    async def get_payout(self, payout_id: UUID) -> PayoutView | None: ...

    # 운영자 상태 전이
    async def list_by_status(self, status: str | None) -> list[PayoutView]: ...
    async def set_status(
        self, payout_id: UUID, status: str, operator_id: UUID | None, now: datetime, memo: str | None = None
    ) -> None: ...
    async def unlink_settlements(self, payout_id: UUID) -> None:
        """반려 시 정산분 회수 — settlement.payout_id 를 NULL 로."""
        ...
