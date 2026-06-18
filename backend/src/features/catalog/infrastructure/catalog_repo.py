"""CatalogRepository 의 SQLAlchemy 구현."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.catalog.domain.models import PUBLISHED, BookSummary
from src.infrastructure.db.models.book import Book


def _to_summary(b: Book) -> BookSummary:
    return BookSummary(
        id=b.id,
        title=b.title,
        subtitle=b.subtitle,
        author_id=b.author_id,
        kind=b.kind,
        language=b.language,
        status=b.status,
        price_amt=int(b.price_amt) if b.price_amt is not None else None,
        cover_url=b.cover_url,
        published_at=b.published_at,
    )


class SqlCatalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary(self, book_id: UUID) -> BookSummary | None:
        b = await self.session.get(Book, book_id)
        return _to_summary(b) if b else None

    async def set_status(self, book_id: UUID, status: str, published_at: datetime | None = None) -> None:
        b = await self.session.get(Book, book_id)
        b.status = status
        if published_at is not None:
            b.published_at = published_at
        await self.session.commit()

    async def set_price(self, book_id: UUID, amount: int) -> None:
        b = await self.session.get(Book, book_id)
        b.price_amt = amount
        await self.session.commit()

    async def set_author(self, book_id: UUID, author_id: UUID) -> None:
        b = await self.session.get(Book, book_id)
        b.author_id = author_id
        await self.session.commit()

    async def list_published(self, q: str | None, limit: int, offset: int) -> list[BookSummary]:
        stmt = select(Book).where(Book.status == PUBLISHED)
        if q:
            stmt = stmt.where(Book.title.ilike(f"%{q}%"))
        stmt = stmt.order_by(Book.published_at.desc()).limit(limit).offset(offset)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_summary(b) for b in rows]
