"""order 리포지토리 포트."""
from typing import Protocol
from uuid import UUID

from src.engine.settlement.calculate import SettlementBreakdown
from src.features.billing.domain.models import OrderView


class OrderRepository(Protocol):
    async def create_order(
        self, book_id: UUID, buyer_account_id: UUID, amount: int, channel: str
    ) -> UUID:
        ...

    async def get_order(self, order_id: UUID) -> OrderView | None:
        ...

    async def mark_paid_with_settlement(
        self, order_id: UUID, pg_provider_cd: str, pg_tx_id: str, breakdown: SettlementBreakdown
    ) -> None:
        """주문을 PAID 로 전이하고 정산 레코드를 함께 기록 (원자적)."""
        ...
