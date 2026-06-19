"""catalog 리포지토리 포트."""
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.features.catalog.domain.models import BookSummary


class CatalogRepository(Protocol):
    async def get_summary(self, book_id: UUID) -> BookSummary | None:
        ...

    async def set_status(self, book_id: UUID, status: str, published_at: datetime | None = None) -> None:
        ...

    async def set_price(self, book_id: UUID, amount: int) -> None:
        ...

    async def set_author(self, book_id: UUID, author_id: UUID) -> None:
        ...

    async def set_isbn(self, book_id: UUID, isbn: str) -> None:
        ...

    async def list_published(
        self, q: str | None, limit: int, offset: int, kind: str | None = None
    ) -> list[BookSummary]:
        ...

    async def list_by_author(self, author_id: UUID) -> list[BookSummary]:
        """작가가 쓴 책 전 상태 목록 (스튜디오용)."""
        ...
