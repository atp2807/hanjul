"""인메모리 OrderRepository + Fake 결제 게이트웨이."""
import uuid
from uuid import UUID

from src.engine.settlement.calculate import SettlementBreakdown
from src.features.billing.domain.models import PAID, PENDING, OrderView


class FakeGateway:
    provider_cd = "FAKE"

    def __init__(self, ok: bool = True):
        self.ok = ok

    async def verify(self, pg_tx_id: str, expected_amount: int) -> bool:
        return self.ok


class FakePricing:
    def __init__(self, price: int | None = 10000):
        self.price = price

    async def get_purchasable_price(self, book_id) -> int | None:
        return self.price


class FakeOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[UUID, OrderView] = {}
        self.settlements: dict[UUID, SettlementBreakdown] = {}

    async def create_order(self, book_id, buyer_account_id, amount, channel) -> UUID:
        oid = uuid.uuid4()
        self.orders[oid] = OrderView(
            id=oid, book_id=book_id, buyer_account_id=buyer_account_id,
            amount_amt=amount, channel_cd=channel, status_cd=PENDING,
        )
        return oid

    async def get_order(self, order_id) -> OrderView | None:
        return self.orders.get(order_id)

    async def mark_paid_with_settlement(self, order_id, pg_provider_cd, pg_tx_id, breakdown) -> None:
        self.orders[order_id].status_cd = PAID
        self.settlements[order_id] = breakdown

    async def owns(self, account_id, book_id) -> bool:
        return any(
            o.buyer_account_id == account_id and o.book_id == book_id and o.status_cd == PAID
            for o in self.orders.values()
        )

    async def list_purchased_books(self, account_id):
        from src.features.billing.domain.models import PurchasedBook

        seen = {}
        for o in self.orders.values():
            if o.buyer_account_id == account_id and o.status_cd == PAID:
                seen[o.book_id] = PurchasedBook(
                    book_id=o.book_id, title="", kind="", price_amt=o.amount_amt, cover_url=None
                )
        return list(seen.values())
