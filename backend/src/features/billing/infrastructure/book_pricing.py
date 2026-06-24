"""BookPricing 의 SQLAlchemy 구현 — 출판본의 유효가(할인 반영) 반환."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.book import Book


class SqlBookPricing:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_purchasable_price(self, book_id: UUID) -> int | None:
        stmt = select(
            Book.price_amt, Book.discount_amt, Book.discount_until
        ).where(Book.id == book_id, Book.status == "PUBLISHED")
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        price, discount, until = row
        # sqlite 는 tz 를 떨궈 naive 로 옴 → UTC 로 간주(postgres 는 aware)
        if until is not None and until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        # 할인가가 설정되고 종료시각이 미래면 할인가가 유효가 (서버 도출 — 클라 못 건드림)
        if discount is not None and until is not None and until > datetime.now(timezone.utc):
            return int(discount)
        return int(price) if price is not None else None
