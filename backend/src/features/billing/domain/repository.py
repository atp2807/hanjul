"""order 리포지토리 포트."""
from typing import Protocol
from uuid import UUID

from src.engine.settlement.calculate import SettlementBreakdown
from src.features.billing.domain.models import OrderView, PurchasedBook, SalesSummary


class OrderRepository(Protocol):
    async def create_order(
        self, book_id: UUID, buyer_account_id: UUID, amount: int, channel: str, consent_at=None
    ) -> UUID:
        ...

    async def get_order(self, order_id: UUID) -> OrderView | None:
        ...

    async def mark_paid_with_settlement(
        self, order_id: UUID, pg_provider: str, pg_tx_id: str, breakdown: SettlementBreakdown
    ) -> None:
        """주문을 PAID 로 전이하고 정산 레코드를 함께 기록 (원자적)."""
        ...

    async def owns(self, account_id: UUID, book_id: UUID) -> bool:
        """계정이 그 책을 구매(PAID)했는지."""
        ...

    async def list_purchased_books(self, account_id: UUID) -> list[PurchasedBook]:
        """계정이 구매한 책 목록 (내 서재)."""
        ...

    async def author_sales(self, author_id: UUID) -> SalesSummary:
        """작가가 쓴 책들의 판매·정산 요약."""
        ...
