"""BookPricing 의 SQLAlchemy 구현 — 출판본 가격만 반환."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.book import Book


class SqlBookPricing:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_purchasable_price(self, book_id: UUID) -> int | None:
        stmt = select(Book.price_amt).where(
            Book.id == book_id, Book.status == "PUBLISHED"
        )
        price = (await self.session.execute(stmt)).scalar_one_or_none()
        return int(price) if price is not None else None
