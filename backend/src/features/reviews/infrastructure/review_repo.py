"""ReviewRepository 의 SQLAlchemy 구현."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.reviews.domain.models import ReviewSummary, ReviewView
from src.infrastructure.db.models.account import Account
from src.infrastructure.db.models.review import Review


class SqlReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, book_id: UUID, account_id: UUID, rating: int, body: str | None) -> None:
        existing = (
            await self.session.execute(
                select(Review).where(Review.book_id == book_id, Review.account_id == account_id)
            )
        ).scalar_one_or_none()
        if existing:
            existing.rating = rating
            existing.body = body
        else:
            self.session.add(Review(book_id=book_id, account_id=account_id, rating=rating, body=body))
        await self.session.commit()

    async def list_for_book(self, book_id: UUID) -> list[ReviewView]:
        stmt = (
            select(Review, Account.display_name)
            .join(Account, Account.id == Review.account_id)
            .where(Review.book_id == book_id)
            .order_by(Review.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            ReviewView(id=r.id, rating=r.rating, body=r.body, author=name, created_at=r.created_at)
            for r, name in rows
        ]

    async def summary(self, book_id: UUID) -> ReviewSummary:
        avg, cnt = (
            await self.session.execute(
                select(func.avg(Review.rating), func.count()).where(Review.book_id == book_id)
            )
        ).one()
        return ReviewSummary(average=round(float(avg), 2) if avg is not None else 0.0, count=cnt or 0)
