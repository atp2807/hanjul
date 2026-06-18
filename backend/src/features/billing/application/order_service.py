"""billing 서비스 — 주문 생성 + 결제확인 → 정산.

결제 확인 시 정산 엔진(engine.settlement)으로 분배/원천징수를 계산해 기록.
"""
from uuid import UUID

from src.engine.settlement.calculate import calculate_settlement
from src.features.billing.domain.gateway import PaymentGateway
from src.features.billing.domain.models import (
    PAID,
    AlreadyPaid,
    OrderNotFound,
    OrderView,
    PaymentFailed,
    SettlementView,
)
from src.features.billing.domain.repository import OrderRepository


class OrderService:
    def __init__(self, repo: OrderRepository, gateway: PaymentGateway, is_individual: bool = True):
        self.repo = repo
        self.gateway = gateway
        self.is_individual = is_individual

    async def create_order(
        self, book_id: UUID, buyer_account_id: UUID, amount: int, channel: str = "SELF"
    ) -> UUID:
        return await self.repo.create_order(book_id, buyer_account_id, amount, channel)

    async def get_order(self, order_id: UUID) -> OrderView:
        order = await self.repo.get_order(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    async def owns(self, account_id: UUID, book_id: UUID) -> bool:
        return await self.repo.owns(account_id, book_id)

    async def list_library(self, account_id: UUID):
        return await self.repo.list_purchased_books(account_id)

    async def confirm_payment(self, order_id: UUID, pg_tx_id: str) -> SettlementView:
        order = await self.get_order(order_id)
        if order.status_cd == PAID:
            raise AlreadyPaid()

        ok = await self.gateway.verify(pg_tx_id, order.amount_amt)
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
