"""billing 서비스 — 주문 생성 + 결제확인 → 정산.

결제 확인 시 정산 엔진(engine.settlement)으로 분배/원천징수를 계산해 기록.
"""
from datetime import UTC, datetime
from uuid import UUID

from src.engine.settlement.calculate import calculate_settlement
from src.features.billing.domain.gateway import PaymentGateway
from src.features.billing.domain.models import (
    PAID,
    AlreadyOwned,
    AlreadyPaid,
    ConsentRequired,
    NotPurchasable,
    NotRefundable,
    OrderNotFound,
    OrderView,
    PaymentFailed,
    RefundFailed,
    SettlementView,
)
from src.features.billing.domain.pricing import BookPricing, BookRatingLookup
from src.features.billing.domain.repository import OrderRepository
from src.features.books.domain.content_rating import (
    AccountTierLookup,
    AgeVerificationRequired,
    is_book_accessible,
)


class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        gateway: PaymentGateway,
        pricing: BookPricing,
        is_individual: bool = True,
        rating_lookup: BookRatingLookup | None = None,
        account_tier: AccountTierLookup | None = None,
    ):
        self.repo = repo
        self.gateway = gateway
        self.pricing = pricing
        self.is_individual = is_individual
        # 연령 게이트(dc-daeb0d3d) 포트 — 미주입이면 등급 조회 없이 안전한 기본값 사용
        # (rating="ALL": 모르는 책은 안 막음 / tier="ALL": 모르는 계정은 최저등급 취급).
        # 실제 요청 경로(get_order_service DI)는 항상 두 포트를 채워 실제 값을 조회한다.
        self.rating_lookup = rating_lookup
        self.account_tier = account_tier

    async def create_order(
        self,
        book_id: UUID,
        buyer_account_id: UUID,
        channel: str = "SELF",
        withdrawal_consent: bool = False,
    ) -> UUID:
        # 전자책 청약철회 제한 동의 필수 (전자상거래법 §17⑥ — 미동의면 주문 불가)
        if not withdrawal_consent:
            raise ConsentRequired()
        # 금액은 서버가 책 가격에서 도출 — 클라가 보낸 값 신뢰 금지 (client_always_transparent)
        price = await self.pricing.get_purchasable_price(book_id)
        if price is None:
            raise NotPurchasable(book_id)
        # 연령 게이트(dc-daeb0d3d) — 항상 검사(포트 미주입이면 안전한 기본값으로).
        rating = "ALL"
        if self.rating_lookup is not None:
            rating = await self.rating_lookup.get_content_rating(book_id) or "ALL"
        tier = "ALL"
        if self.account_tier is not None:
            tier = await self.account_tier.get_verified_tier(buyer_account_id)
        if not is_book_accessible(rating, tier):
            raise AgeVerificationRequired()
        if await self.repo.owns(buyer_account_id, book_id):
            raise AlreadyOwned()
        return await self.repo.create_order(
            book_id, buyer_account_id, price, channel, consent_at=datetime.now(UTC)
        )

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
        if order.status != PAID:
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
        if order is None or order.status != PAID or not order.pg_tx_id:
            return False
        status = await self.gateway.lookup_status(order.pg_tx_id)
        if status in ("CANCELED", "CANCELLED", "PARTIAL_CANCELED"):
            return await self.repo.mark_refunded(order_id)
        return False

    async def owns(self, account_id: UUID, book_id: UUID) -> bool:
        return await self.repo.owns(account_id, book_id)

    async def has_any_order(self, book_id: UUID) -> bool:
        """이 책에 주문이 하나라도 있나 — 책 삭제 가능 판정용."""
        return await self.repo.has_any_order(book_id)

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
        if order.status == PAID:
            raise AlreadyPaid()

        # order_ref = 토스 orderId 등 PG가 결제 시 식별자로 쓴 값(우리 주문 UUID)
        ok = await self.gateway.verify(pg_tx_id, order.amount_amt, order_ref=str(order_id))
        if not ok:
            raise PaymentFailed()

        breakdown = calculate_settlement(order.amount_amt, order.channel, self.is_individual)
        await self.repo.mark_paid_with_settlement(
            order_id, self.gateway.provider_cd, pg_tx_id, breakdown
        )
        return SettlementView(
            channel=breakdown.channel,
            gross_amt=breakdown.author_gross,
            platform_fee_amt=breakdown.platform_fee,
            withholding_amt=breakdown.withholding,
            payout_amt=breakdown.payout,
        )
