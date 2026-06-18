"""CoverRepository 의 SQLAlchemy 구현."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.book import Book


class SqlCoverRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def book_exists(self, book_id: UUID) -> bool:
        return await self.session.get(Book, book_id) is not None

    async def set_cover(self, book_id: UUID, cover_url: str) -> None:
        book = await self.session.get(Book, book_id)
        book.cover_url = cover_url
        await self.session.commit()
