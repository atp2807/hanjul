"""catalog 서비스 — 출판 라이프사이클 + 스토어 조회."""
from datetime import datetime, timezone
from uuid import UUID

from src.features.catalog.domain.models import (
    BookNotFound,
    BookSummary,
    InvalidTransition,
    PriceRequired,
    DRAFT,
    PUBLISHED,
    REVIEW,
)
from src.features.catalog.domain.repository import CatalogRepository


class CatalogService:
    def __init__(self, repo: CatalogRepository):
        self.repo = repo

    async def _require(self, book_id: UUID) -> BookSummary:
        summary = await self.repo.get_summary(book_id)
        if summary is None:
            raise BookNotFound(book_id)
        return summary

    async def assign_author(self, book_id: UUID, author_id: UUID) -> None:
        await self._require(book_id)
        await self.repo.set_author(book_id, author_id)

    async def set_price(self, book_id: UUID, amount: int) -> None:
        await self._require(book_id)
        if amount < 0:
            raise ValueError("price must be >= 0")
        await self.repo.set_price(book_id, amount)

    async def submit_for_review(self, book_id: UUID) -> None:
        s = await self._require(book_id)
        if s.status != DRAFT:
            raise InvalidTransition(s.status, REVIEW)
        await self.repo.set_status(book_id, REVIEW)

    async def publish(self, book_id: UUID, now: datetime | None = None) -> None:
        s = await self._require(book_id)
        if s.status != REVIEW:
            raise InvalidTransition(s.status, PUBLISHED)
        if s.price_amt is None:
            raise PriceRequired()
        await self.repo.set_status(book_id, PUBLISHED, now or datetime.now(timezone.utc))

    async def list_store(
        self, q: str | None = None, kind: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[BookSummary]:
        return await self.repo.list_published(q, limit, offset, kind)

    async def get_store_detail(self, book_id: UUID) -> BookSummary:
        s = await self._require(book_id)
        if s.status != PUBLISHED:
            raise BookNotFound(book_id)  # 미출판 책은 스토어에 비공개
        return s
