"""billing 도메인 — 주문/정산 뷰 + 에러."""
from dataclasses import dataclass
from uuid import UUID

from src.shared.errors import DomainError

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
    channel: str
    status: str
    pg_tx_id: str | None = None


@dataclass
class SettlementView:
    channel: str
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


class BillingError(DomainError):
    """billing 도메인 예외 베이스."""


class OrderNotFound(BillingError):
    status_code = 404
    def __init__(self, order_id: UUID | None = None):
        super().__init__("주문을 찾을 수 없어요.")


class AlreadyPaid(BillingError):
    status_code = 409
    default_detail = "이미 결제된 주문이에요."


class PaymentFailed(BillingError):
    status_code = 402
    default_detail = "결제 확인에 실패했어요."


class NotPurchasable(BillingError):
    """책이 구매 불가 (미출판이거나 가격 미설정)."""
    status_code = 404
    def __init__(self, book_id=None):
        super().__init__("구매할 수 없는 책이에요.")


class AlreadyOwned(BillingError):
    """이미 구매한 책 (중복 구매 방지)."""
    status_code = 409
    default_detail = "이미 보유한 책이에요."


class ConsentRequired(BillingError):
    """청약철회 제한 동의 없이 주문 시도 (전자상거래법 §17⑥)."""
    status_code = 422
    default_detail = "청약철회 제한 동의가 필요해요."


class NotRefundable(BillingError):
    """환불 불가 (미결제이거나 이미 환불됨)."""
    status_code = 409
    default_detail = "환불할 수 없는 주문이에요."


class RefundFailed(BillingError):
    """PG 환불 거절."""
    status_code = 402
    default_detail = "환불 처리에 실패했어요."
