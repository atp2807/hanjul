"""payouts 도메인 — 작가 출금계좌 + 출금 배치.

흐름: 계좌 등록 → 미지급 정산분 집계(출금 가능액) → 출금 신청(payout, REQUESTED)
     → 운영자 승인(APPROVED) → 실이체 후 지급완료(PAID). 반려(REJECTED)면 정산분 회수.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.errors import ConflictError, NotFoundError, ValidationError

# payout 상태기계
REQUESTED = "REQUESTED"
APPROVED = "APPROVED"
PAID = "PAID"
REJECTED = "REJECTED"


@dataclass
class BankAccountView:
    id: UUID
    holder_name: str
    bank: str
    account_no_masked: str


@dataclass
class PayoutView:
    id: UUID
    author_id: UUID
    status: str
    gross_amt: int
    withholding_amt: int
    net_amt: int
    holder_name: str | None
    bank: str | None
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


class NoBankAccount(ValidationError):
    """출금계좌 미등록 상태에서 출금 신청 (422)."""
    default_detail = "출금계좌를 먼저 등록해 주세요."


class NothingToPayout(ValidationError):
    """출금 가능 잔액 없음 (422)."""
    default_detail = "출금 가능한 정산 잔액이 없어요."


class PayoutNotFound(NotFoundError):
    default_detail = "출금 신청을 찾을 수 없어요."


class InvalidPayoutState(ConflictError):
    """상태기계 위반 (예: 이미 지급된 건 재승인) (409)."""
    default_detail = "처리할 수 없는 상태예요."


class PayoutReportHook(Protocol):
    """PAID 전이 후 best-effort 훅(예: woncheon 원천징수 신고 커넥터, lr-ac61f505).

    payouts 도메인은 구체 구현(woncheon 등)을 모른다 — DI(presentation/dependencies.py)가
    주입. 실패해도 지급 자체(PAID 전이)는 막지 않도록 PayoutService가 방어적으로 감싼다.
    """
    async def on_paid(self, payout_id: UUID) -> None: ...


class PayoutRepository(Protocol):
    # 계좌
    async def get_bank_account(self, account_id: UUID) -> BankAccountView | None: ...
    async def upsert_bank_account(
        self, account_id: UUID, holder_name: str, bank: str, account_no_enc: str, account_no_masked: str
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
    async def transition(
        self,
        payout_id: UUID,
        from_statuses: tuple[str, ...],
        to_status: str,
        operator_id: UUID | None,
        now: datetime,
        memo: str | None = None,
    ) -> bool:
        """행 잠금 후 상태 전이 (from_statuses 밖이면 False — 동시 승인/지급 방지).

        REJECTED 전이는 정산분 회수(settlement.payout_id NULL)까지 같은 트랜잭션.
        """
        ...
