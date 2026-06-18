"""OrderRepository 의 SQLAlchemy 구현."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.settlement.calculate import SettlementBreakdown
from src.features.billing.domain.models import OrderView, PurchasedBook
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.order import Order, Settlement


class SqlOrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, book_id: UUID, buyer_account_id: UUID, amount: int, channel: str) -> UUID:
        order = Order(
            book_id=book_id,
            buyer_account_id=buyer_account_id,
            amount_amt=amount,
            channel_cd=channel,
            status_cd="PENDING",
        )
        self.session.add(order)
        await self.session.flush()
        await self.session.commit()
        return order.id

    async def get_order(self, order_id: UUID) -> OrderView | None:
        o = await self.session.get(Order, order_id)
        if o is None:
            return None
        return OrderView(
            id=o.id,
            book_id=o.book_id,
            buyer_account_id=o.buyer_account_id,
            amount_amt=int(o.amount_amt),
            channel_cd=o.channel_cd,
            status_cd=o.status_cd,
        )

    async def mark_paid_with_settlement(
        self, order_id: UUID, pg_provider_cd: str, pg_tx_id: str, breakdown: SettlementBreakdown
    ) -> None:
        o = await self.session.get(Order, order_id)
        o.status_cd = "PAID"
        o.pg_provider_cd = pg_provider_cd
        o.pg_tx_id = pg_tx_id
        o.paid_at = datetime.now(timezone.utc)
        self.session.add(
            Settlement(
                order_id=order_id,
                channel_cd=breakdown.channel,
                gross_amt=breakdown.author_gross,
                platform_fee_amt=breakdown.platform_fee,
                withholding_amt=breakdown.withholding,
                payout_amt=breakdown.payout,
            )
        )
        await self.session.commit()

    async def owns(self, account_id, book_id) -> bool:
        stmt = (
            select(Order.id)
            .where(
                Order.buyer_account_id == account_id,
                Order.book_id == book_id,
                Order.status_cd == "PAID",
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def list_purchased_books(self, account_id) -> list[PurchasedBook]:
        stmt = (
            select(Book)
            .join(Order, Order.book_id == Book.id)
            .where(Order.buyer_account_id == account_id, Order.status_cd == "PAID")
            .distinct()
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            PurchasedBook(
                book_id=b.id,
                title=b.title,
                kind=b.kind,
                price_amt=int(b.price_amt) if b.price_amt is not None else None,
                cover_url=b.cover_url,
            )
            for b in rows
        ]
