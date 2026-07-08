"""인메모리 OrderRepository + Fake 결제 게이트웨이."""
import uuid
from uuid import UUID

from src.engine.settlement.calculate import SettlementBreakdown
from src.features.billing.domain.models import PAID, PENDING, OrderView


class FakeGateway:
    provider_cd = "FAKE"

    def __init__(self, ok: bool = True):
        self.ok = ok

    async def verify(self, pg_tx_id: str, expected_amount: int, order_ref: str | None = None) -> bool:
        return self.ok

    async def refund(self, pg_tx_id: str, reason: str, order_ref: str | None = None) -> bool:
        return self.ok

    async def lookup_status(self, pg_tx_id: str) -> str | None:
        return getattr(self, "status", None)  # 테스트에서 .status 세팅


class FakePricing:
    def __init__(self, price: int | None = 10000, rating: str | None = "ALL"):
        self.price = price
        self.rating = rating  # 연령 게이트(dc-daeb0d3d) — get_content_rating 기본값

    async def get_purchasable_price(self, book_id) -> int | None:
        return self.price

    async def get_content_rating(self, book_id) -> str | None:
        return self.rating


class FakeAccountTier:
    """AccountTierLookup 포트의 최소 구현 — 연령 게이트(dc-daeb0d3d) 테스트용."""

    def __init__(self, tiers: dict | None = None) -> None:
        self.tiers = tiers or {}

    async def get_verified_tier(self, account_id) -> str:
        return self.tiers.get(account_id, "ALL")


class FakeOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[UUID, OrderView] = {}
        self.settlements: dict[UUID, SettlementBreakdown] = {}
        self.delivered: set[UUID] = set()  # mark_delivered 호출된 order id (order.delivered_ts 대역)

    async def create_order(self, book_id, buyer_account_id, amount, channel, consent_at=None) -> UUID:
        oid = uuid.uuid4()
        self.orders[oid] = OrderView(
            id=oid, book_id=book_id, buyer_account_id=buyer_account_id,
            amount_amt=amount, channel=channel, status=PENDING,
        )
        return oid

    async def get_order(self, order_id) -> OrderView | None:
        return self.orders.get(order_id)

    async def mark_paid_with_settlement(self, order_id, pg_provider_cd, pg_tx_id, breakdown) -> None:
        self.orders[order_id].status = PAID
        self.settlements[order_id] = breakdown

    async def owns(self, account_id, book_id) -> bool:
        return any(
            o.buyer_account_id == account_id and o.book_id == book_id and o.status == PAID
            for o in self.orders.values()
        )

    async def mark_delivered(self, buyer_id, book_id) -> None:
        for o in self.orders.values():
            if o.buyer_account_id == buyer_id and o.book_id == book_id and o.status == PAID:
                self.delivered.add(o.id)

    async def is_settlement_paid_out(self, order_id) -> bool:
        return False  # Fake는 payout 연결을 모델링하지 않음 — 항상 미지급 취급

    async def grant_review_copy(self, book_id, account_id) -> None:
        if await self.owns(account_id, book_id):
            return
        oid = uuid.uuid4()
        self.orders[oid] = OrderView(
            id=oid, book_id=book_id, buyer_account_id=account_id,
            amount_amt=0, channel="REVIEW", status=PAID,
        )

    async def is_review_copy(self, account_id, book_id) -> bool:
        return any(
            o.buyer_account_id == account_id and o.book_id == book_id
            and o.status == PAID and o.channel == "REVIEW"
            for o in self.orders.values()
        )

    async def buyer_ids(self, book_id) -> list:
        return list(
            {o.buyer_account_id for o in self.orders.values() if o.book_id == book_id and o.status == PAID}
        )

    async def author_sales(self, author_id):
        from src.features.billing.domain.models import SalesSummary

        return SalesSummary(total_orders=0, total_revenue=0, total_payout=0, books=[])

    async def list_purchased_books(self, account_id):
        from src.features.billing.domain.models import PurchasedBook

        seen = {}
        for o in self.orders.values():
            if o.buyer_account_id == account_id and o.status == PAID:
                seen[o.book_id] = PurchasedBook(
                    book_id=o.book_id, title="", kind="", price_amt=o.amount_amt, cover_url=None, order_id=o.id
                )
        return list(seen.values())
