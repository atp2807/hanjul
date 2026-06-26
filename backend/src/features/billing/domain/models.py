"""billing 도메인 — 주문/정산 뷰 + 에러."""
from dataclasses import dataclass
from uuid import UUID

PENDING = "PENDING"
PAID = "PAID"
CANCELLED = "CANCELLED"
REFUNDED = "REFUNDED"

# 판매 채널 (정산 분배). REVIEW=서평단 증정본(0원, 분배·매출 제외, 리뷰 권한만).
SELF = "SELF"
EXTERNAL = "EXTERNAL"
REVIEW = "REVIEW"


@dataclass
class OrderView:
    id: UUID
    book_id: UUID
    buyer_account_id: UUID
    amount_amt: int
    channel_cd: str
    status_cd: str
    pg_tx_id: str | None = None


@dataclass
class SettlementView:
    channel_cd: str
    gross_amt: int
    platform_fee_amt: int
    withholding_amt: int
    payout_amt: int


@dataclass
class PurchasedBook:
    """내 서재 항목 — 구매한 책의 요약 + 그 구매의 주문 id(환불용)."""
    book_id: UUID
    title: str
    kind: str
    price_amt: int | None
    cover_url: str | None
    order_id: UUID


@dataclass
class BookSales:
    book_id: UUID
    title: str
    order_count: int
    revenue: int   # 총 판매액
    payout: int    # 작가 실지급 합


@dataclass
class SalesSummary:
    total_orders: int
    total_revenue: int
    total_payout: int
    books: list[BookSales]


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


class NotPurchasable(BillingError):
    """책이 구매 불가 (미출판이거나 가격 미설정)."""
    def __init__(self, book_id):
        super().__init__(f"book not purchasable: {book_id}")


class AlreadyOwned(BillingError):
    """이미 구매한 책 (중복 구매 방지)."""
    def __init__(self):
        super().__init__("already owned")


class NotRefundable(BillingError):
    """환불 불가 (미결제이거나 이미 환불됨)."""
    def __init__(self):
        super().__init__("order not refundable")


class RefundFailed(BillingError):
    """PG 환불 거절."""
    def __init__(self):
        super().__init__("refund failed at gateway")
