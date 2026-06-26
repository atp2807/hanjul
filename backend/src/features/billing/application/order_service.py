"""billing 서비스 — 주문 생성 + 결제확인 → 정산.

결제 확인 시 정산 엔진(engine.settlement)으로 분배/원천징수를 계산해 기록.
"""
from uuid import UUID

from src.engine.settlement.calculate import calculate_settlement
from src.features.billing.domain.gateway import PaymentGateway
from src.features.billing.domain.models import (
    PAID,
    AlreadyOwned,
    AlreadyPaid,
    NotPurchasable,
    NotRefundable,
    OrderNotFound,
    OrderView,
    PaymentFailed,
    RefundFailed,
    SettlementView,
)
from src.features.billing.domain.pricing import BookPricing
from src.features.billing.domain.repository import OrderRepository


class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        gateway: PaymentGateway,
        pricing: BookPricing,
        is_individual: bool = True,
    ):
        self.repo = repo
        self.gateway = gateway
        self.pricing = pricing
        self.is_individual = is_individual

    async def create_order(
        self, book_id: UUID, buyer_account_id: UUID, channel: str = "SELF"
    ) -> UUID:
        # 금액은 서버가 책 가격에서 도출 — 클라가 보낸 값 신뢰 금지 (client_always_transparent)
        price = await self.pricing.get_purchasable_price(book_id)
        if price is None:
            raise NotPurchasable(book_id)
        if await self.repo.owns(buyer_account_id, book_id):
            raise AlreadyOwned()
        return await self.repo.create_order(book_id, buyer_account_id, price, channel)

    async def get_order(self, order_id: UUID) -> OrderView:
        order = await self.repo.get_order(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    async def refund(self, order_id: UUID, buyer_id: UUID, reason: str = "") -> None:
        """구매자 본인 환불 — PG 취소 후 PAID→REFUNDED (서재·매출·알림서 자동 제외)."""
        order = await self.get_order(order_id)
        if order.buyer_account_id != buyer_id:
            raise OrderNotFound(order_id)  # 타인 주문은 존재 노출 없이 404
        if order.status_cd != PAID:
            raise NotRefundable()
        ok = await self.gateway.refund(order.pg_tx_id, reason or "구매자 환불", order_ref=str(order_id))
        if not ok:
            raise RefundFailed()
        if not await self.repo.mark_refunded(order_id):
            raise NotRefundable()  # 동시 환불 경쟁 → 이미 처리됨

    async def reconcile_canceled(self, order_id: UUID) -> bool:
        """웹훅 reconcile — 바디 불신. PG에서 실제 상태 재조회해 취소면 PAID→REFUNDED.

        주문의 '우리 DB에 저장된' pg_tx_id로만 조회 → 위조 바디로 남의 주문 못 건드림.
        """
        order = await self.repo.get_order(order_id)
        if order is None or order.status_cd != PAID or not order.pg_tx_id:
            return False
        status = await self.gateway.lookup_status(order.pg_tx_id)
        if status in ("CANCELED", "CANCELLED", "PARTIAL_CANCELED"):
            return await self.repo.mark_refunded(order_id)
        return False

    async def owns(self, account_id: UUID, book_id: UUID) -> bool:
        return await self.repo.owns(account_id, book_id)

    async def grant_review_copy(self, book_id: UUID, account_id: UUID) -> None:
        """서평단 증정본 지급 — 0원 권한(분배·매출 없음). 리뷰 작성 가능해짐."""
        await self.repo.grant_review_copy(book_id, account_id)

    async def is_review_copy(self, account_id: UUID, book_id: UUID) -> bool:
        return await self.repo.is_review_copy(account_id, book_id)

    async def buyer_ids(self, book_id: UUID) -> list[UUID]:
        """이 책 구매자 계정 id — 개정판 알림 대상."""
        return await self.repo.buyer_ids(book_id)

    async def list_library(self, account_id: UUID):
        return await self.repo.list_purchased_books(account_id)

    async def author_sales(self, author_id: UUID):
        return await self.repo.author_sales(author_id)

    async def confirm_payment(
        self, order_id: UUID, pg_tx_id: str, buyer_id: UUID | None = None
    ) -> SettlementView:
        order = await self.get_order(order_id)
        # 남의 주문은 못 본 것처럼 처리 (존재 노출 최소화)
        if buyer_id is not None and order.buyer_account_id != buyer_id:
            raise OrderNotFound(order_id)
        if order.status_cd == PAID:
            raise AlreadyPaid()

        # order_ref = 토스 orderId 등 PG가 결제 시 식별자로 쓴 값(우리 주문 UUID)
        ok = await self.gateway.verify(pg_tx_id, order.amount_amt, order_ref=str(order_id))
        if not ok:
            raise PaymentFailed()

        breakdown = calculate_settlement(order.amount_amt, order.channel_cd, self.is_individual)
        await self.repo.mark_paid_with_settlement(
            order_id, self.gateway.provider_cd, pg_tx_id, breakdown
        )
        return SettlementView(
            channel_cd=breakdown.channel,
            gross_amt=breakdown.author_gross,
            platform_fee_amt=breakdown.platform_fee,
            withholding_amt=breakdown.withholding,
            payout_amt=breakdown.payout,
        )
