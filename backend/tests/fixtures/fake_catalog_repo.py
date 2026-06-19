"""인메모리 CatalogRepository."""
from datetime import datetime
from uuid import UUID

from src.features.catalog.domain.models import PUBLISHED, BookSummary


class FakeCatalogRepository:
    def __init__(self) -> None:
        self.books: dict[UUID, BookSummary] = {}

    def seed(self, summary: BookSummary) -> None:
        self.books[summary.id] = summary

    async def get_summary(self, book_id: UUID) -> BookSummary | None:
        return self.books.get(book_id)

    async def set_status(self, book_id: UUID, status: str, published_at: datetime | None = None) -> None:
        b = self.books[book_id]
        b.status = status
        if published_at is not None:
            b.published_at = published_at

    async def set_price(self, book_id: UUID, amount: int) -> None:
        self.books[book_id].price_amt = amount

    async def set_author(self, book_id: UUID, author_id: UUID) -> None:
        self.books[book_id].author_id = author_id

    async def set_isbn(self, book_id: UUID, isbn: str) -> None:
        self.books[book_id].isbn = isbn

    async def list_by_author(self, author_id):
        return [b for b in self.books.values() if b.author_id == author_id]

    async def list_published(self, q, limit, offset, kind=None) -> list[BookSummary]:
        rows = [b for b in self.books.values() if b.status == PUBLISHED]
        if q:
            rows = [b for b in rows if q.lower() in b.title.lower()]
        if kind:
            rows = [b for b in rows if b.kind == kind]
        return rows[offset : offset + limit]
