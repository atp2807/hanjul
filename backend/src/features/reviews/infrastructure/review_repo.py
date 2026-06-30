"""ReviewRepository 의 SQLAlchemy 구현."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.reviews.domain.models import ReviewSummary, ReviewView
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.review import Review


class SqlReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def book_exists(self, book_id: UUID) -> bool:
        return await self.session.get(Book, book_id) is not None

    async def _find(self, book_id: UUID, account_id: UUID):
        return (
            await self.session.execute(
                select(Review).where(Review.book_id == book_id, Review.account_id == account_id)
            )
        ).scalar_one_or_none()

    async def upsert(
        self, book_id: UUID, account_id: UUID, rating: int, body: str | None, source_cd: str = "PURCHASE"
    ) -> None:
        existing = await self._find(book_id, account_id)
        if existing:
            existing.rating, existing.body, existing.source_cd = rating, body, source_cd
            await self.session.commit()
            return
        self.session.add(Review(book_id=book_id, account_id=account_id, rating=rating, body=body, source_cd=source_cd))
        try:
            await self.session.commit()
        except IntegrityError:
            # 동시 삽입 경쟁(유니크 위반) → 롤백 후 갱신으로 처리(멱등)
            await self.session.rollback()
            again = await self._find(book_id, account_id)
            if again:
                again.rating, again.body, again.source_cd = rating, body, source_cd
                await self.session.commit()

    async def list_for_book(self, book_id: UUID) -> list[ReviewView]:
        stmt = (
            select(Review)
            .where(Review.book_id == book_id)
            .order_by(Review.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            ReviewView(
                id=r.id, rating=r.rating, body=r.body, account_id=r.account_id,
                created_at=r.created_at, updated_at=r.updated_at, source_cd=r.source_cd,
            )
            for r in rows
        ]

    async def summary(self, book_id: UUID) -> ReviewSummary:
        avg, cnt = (
            await self.session.execute(
                select(func.avg(Review.rating), func.count()).where(Review.book_id == book_id)
            )
        ).one()
        return ReviewSummary(average=round(float(avg), 2) if avg is not None else 0.0, count=cnt or 0)
