"""CatalogRepository 의 SQLAlchemy 구현."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.catalog.domain.models import PUBLISHED, BookHasOrders, BookSummary
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
        isbn=b.isbn,
        description=b.description,
        category=b.category,
        discount_amt=int(b.discount_amt) if b.discount_amt is not None else None,
        discount_until=b.discount_until,
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

    async def delete(self, book_id: UUID) -> None:
        b = await self.session.get(Book, book_id)
        if b is None:
            return
        await self.session.delete(b)
        try:
            await self.session.commit()  # 주문(RESTRICT) 있으면 IntegrityError
        except IntegrityError:
            await self.session.rollback()
            raise BookHasOrders()

    async def set_price(self, book_id: UUID, amount: int) -> None:
        b = await self.session.get(Book, book_id)
        b.price_amt = amount
        await self.session.commit()

    async def set_author(self, book_id: UUID, author_id: UUID) -> None:
        b = await self.session.get(Book, book_id)
        b.author_id = author_id
        await self.session.commit()

    async def set_isbn(self, book_id: UUID, isbn: str) -> None:
        b = await self.session.get(Book, book_id)
        b.isbn = isbn
        await self.session.commit()

    async def set_discount(self, book_id: UUID, amount, until) -> None:
        b = await self.session.get(Book, book_id)
        b.discount_amt = amount
        b.discount_until = until
        await self.session.commit()

    async def update_meta(
        self,
        book_id: UUID,
        subtitle: str | None,
        description: str | None,
        category: str | None,
    ) -> None:
        b = await self.session.get(Book, book_id)
        b.subtitle = subtitle
        b.description = description
        b.category = category
        await self.session.commit()

    async def set_scheduled(self, book_id, when) -> None:
        b = await self.session.get(Book, book_id)
        b.scheduled_publish_at = when
        await self.session.commit()

    async def publish_due(self, now) -> list[tuple]:
        """예약 시각이 지난 미출판 책들을 자동 게시. 게시된 (book_id, author_id, title) 목록 반환."""
        stmt = select(Book).where(
            Book.scheduled_publish_at.isnot(None),
            Book.scheduled_publish_at <= now,
            Book.status != PUBLISHED,
            Book.price_amt.isnot(None),
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        published = []
        for b in rows:
            b.status = PUBLISHED
            b.published_at = now
            b.scheduled_publish_at = None
            published.append((b.id, b.author_id, b.title))
        await self.session.commit()
        return published

    async def list_published(
        self, q: str | None, limit: int, offset: int, kind: str | None = None
    ) -> list[BookSummary]:
        stmt = select(Book).where(Book.status == PUBLISHED)
        if q:
            stmt = stmt.where(Book.title.ilike(f"%{q}%"))
        if kind:
            stmt = stmt.where(Book.kind == kind)
        stmt = stmt.order_by(Book.published_at.desc()).limit(limit).offset(offset)  # 최신순
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_summary(b) for b in rows]

    async def list_by_author(self, author_id):
        stmt = (
            select(Book)
            .where(Book.author_id == author_id)
            .order_by(Book.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_summary(b) for b in rows]

    async def list_published_by_author(self, author_id) -> list[BookSummary]:
        """작가의 출판본만 (공개 프로필용, 최신순)."""
        stmt = (
            select(Book)
            .where(Book.author_id == author_id, Book.status == PUBLISHED)
            .order_by(Book.published_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_summary(b) for b in rows]
