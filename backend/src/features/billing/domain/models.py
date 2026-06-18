"""billing 도메인 — 주문/정산 뷰 + 에러."""
from dataclasses import dataclass
from uuid import UUID

PENDING = "PENDING"
PAID = "PAID"
CANCELLED = "CANCELLED"


@dataclass
class OrderView:
    id: UUID
    book_id: UUID
    buyer_account_id: UUID
    amount_amt: int
    channel_cd: str
    status_cd: str


@dataclass
class SettlementView:
    channel_cd: str
    gross_amt: int
    platform_fee_amt: int
    withholding_amt: int
    payout_amt: int


@dataclass
class PurchasedBook:
    """내 서재 항목 — 구매한 책의 요약."""
    book_id: UUID
    title: str
    kind: str
    price_amt: int | None
    cover_url: str | None


class BillingError(Exception):
    pass


class OrderNotFound(BillingError):
    def __init__(self, order_id: UUID):
        super().__init__(f"order not found: {order_id}")


class AlreadyPaid(BillingError):
    def __init__(self):
        super().__init__("order already paid")


class PaymentFailed(BillingError):
    def __init__(self):
        super().__init__("payment verification failed")
