"""인메모리 CatalogRepository."""
from datetime import datetime
from uuid import UUID

from src.features.books.domain.content_rating import TIERS, tier_rank
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

    async def set_isbn(self, book_id: UUID, isbn: str) -> None:
        self.books[book_id].isbn = isbn

    async def set_discount(self, book_id: UUID, amount, until) -> None:
        self.books[book_id].discount_amt = amount
        self.books[book_id].discount_until = until

    async def set_scheduled(self, book_id, when) -> None:
        self.scheduled = getattr(self, "scheduled", {})
        self.scheduled[book_id] = when

    async def publish_due(self, now) -> list:
        return []  # 예약 게시 로직은 통합테스트(실 DB)에서 검증

    async def list_by_author(self, author_id):
        return [b for b in self.books.values() if b.author_id == author_id]

    async def list_published_by_author(self, author_id) -> list[BookSummary]:
        return [b for b in self.books.values() if b.author_id == author_id and b.status == PUBLISHED]

    async def list_published(
        self, q, limit, offset, kind=None, category=None, account_tier="ALL"
    ) -> list[BookSummary]:
        rows = [b for b in self.books.values() if b.status == PUBLISHED]
        if q:
            rows = [b for b in rows if q.lower() in b.title.lower()]
        if kind:
            rows = [b for b in rows if b.kind == kind]
        if category:
            rows = [b for b in rows if b.category == category]
        # 연령 게이트(dc-daeb0d3d) — 실 SqlCatalogRepository.list_published와 동일한 필터.
        allowed = TIERS[: tier_rank(account_tier) + 1]
        rows = [b for b in rows if b.content_rating in allowed]
        return rows[offset : offset + limit]
