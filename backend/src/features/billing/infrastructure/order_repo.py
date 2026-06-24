"""OrderRepository 의 SQLAlchemy 구현."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engine.settlement.calculate import SettlementBreakdown
from src.features.billing.domain.models import BookSales, OrderView, PurchasedBook, SalesSummary
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
        # 행 잠금 + 상태 재확인 — 동시 confirm 2건이 둘 다 PAID/정산 2중 기록되는 레이스 차단.
        # (이미 PAID면 멱등 no-op: 토스 idempotency 로 실제 청구는 1회.)
        o = (
            await self.session.execute(
                select(Order)
                .where(Order.id == order_id)
                .with_for_update()
                .execution_options(populate_existing=True)  # 잠금 후 DB 최신값으로 갱신
            )
        ).scalar_one_or_none()
        if o is None or o.status_cd == "PAID":
            await self.session.rollback()
            return
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

    async def buyer_ids(self, book_id) -> list:
        """이 책을 구매(PAID)한 계정 id 목록 — 개정판 알림 대상."""
        rows = (
            await self.session.execute(
                select(Order.buyer_account_id)
                .where(Order.book_id == book_id, Order.status_cd == "PAID")
                .distinct()
            )
        ).scalars().all()
        return list(rows)

    async def author_sales(self, author_id) -> SalesSummary:
        stmt = (
            select(
                Book.id,
                Book.title,
                func.count(Settlement.id),
                func.coalesce(func.sum(Order.amount_amt), 0),
                func.coalesce(func.sum(Settlement.payout_amt), 0),
            )
            .select_from(Settlement)
            .join(Order, Order.id == Settlement.order_id)
            .join(Book, Book.id == Order.book_id)
            .where(Book.author_id == author_id)
            .group_by(Book.id, Book.title)
        )
        rows = (await self.session.execute(stmt)).all()
        books = [
            BookSales(book_id=r[0], title=r[1], order_count=r[2], revenue=int(r[3]), payout=int(r[4]))
            for r in rows
        ]
        return SalesSummary(
            total_orders=sum(b.order_count for b in books),
            total_revenue=sum(b.revenue for b in books),
            total_payout=sum(b.payout for b in books),
            books=books,
        )

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
