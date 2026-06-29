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

    async def delete(self, book_id: UUID) -> None:
        """책 삭제 (장·블록 등 CASCADE). 주문 있으면 FK RESTRICT → BookHasOrders."""
        ...

    async def set_price(self, book_id: UUID, amount: int) -> None:
        ...

    async def set_author(self, book_id: UUID, author_id: UUID) -> None:
        ...

    async def set_isbn(self, book_id: UUID, isbn: str) -> None:
        ...

    async def set_discount(self, book_id: UUID, amount, until) -> None:
        ...

    async def update_meta(
        self, book_id: UUID, subtitle: str | None, description: str | None, category: str | None
    ) -> None:
        ...

    async def set_scheduled(self, book_id: UUID, when) -> None:
        ...

    async def publish_due(self, now) -> list[tuple]:
        """게시된 (book_id, author_id, title) 목록 반환."""
        ...

    async def list_published(
        self, q: str | None, limit: int, offset: int, kind: str | None = None
    ) -> list[BookSummary]:
        ...

    async def list_by_author(self, author_id: UUID) -> list[BookSummary]:
        """작가가 쓴 책 전 상태 목록 (스튜디오용)."""
        ...
