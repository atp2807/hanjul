"""billing API 스키마 (camelCase)."""
from uuid import UUID

from src.presentation.schema import CamelSchema


class CreateOrderRequest(CamelSchema):
    book_id: UUID
    channel: str = "SELF"  # SELF | EXTERNAL
    # 전자책 청약철회 제한 동의 (전자상거래법 §17⑥) — 미동의면 주문 거부(422)
    withdrawal_consent: bool = False
    # 금액·구매자는 서버가 결정 (책 가격 + 인증된 사용자) — 클라가 못 보냄


class OrderResponse(CamelSchema):
    id: UUID
    book_id: UUID
    buyer_account_id: UUID
    amount_amt: int
    channel_cd: str
    status_cd: str


class ConfirmPaymentRequest(CamelSchema):
    pg_tx_id: str


class SettlementResponse(CamelSchema):
    channel_cd: str
    gross_amt: int
    platform_fee_amt: int
    withholding_amt: int
    payout_amt: int


class LibraryItemResponse(CamelSchema):
    book_id: UUID
    title: str
    kind: str
    price_amt: int | None
    cover_url: str | None
    order_id: UUID


class BookSalesResponse(CamelSchema):
    book_id: UUID
    title: str
    order_count: int
    revenue: int
    payout: int


class SalesSummaryResponse(CamelSchema):
    total_orders: int
    total_revenue: int
    total_payout: int
    books: list[BookSalesResponse]
