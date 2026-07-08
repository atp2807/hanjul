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

    async def set_blocked(self, book_id: UUID, blocked_at: datetime | None) -> None:
        """운영자 takedown(시각) / 복원(None)."""
        ...

    async def list_for_ops(
        self, q: str | None, status: str | None, limit: int, offset: int
    ) -> list[BookSummary]:
        """운영자 모더레이션 목록 (차단 포함 전 상태)."""
        ...

    async def delete(self, book_id: UUID) -> None:
        """책 삭제 (장·블록 등 CASCADE). 주문 있으면 FK RESTRICT → BookHasOrders."""
        ...

    async def set_price(self, book_id: UUID, amount: int) -> None:
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
        self,
        q: str | None,
        limit: int,
        offset: int,
        kind: str | None = None,
        category: str | None = None,
        account_tier: str = "ALL",
    ) -> list[BookSummary]:
        """account_tier 미만 인증등급으로는 볼 수 없는 등급의 책은 제외(dc-daeb0d3d)."""
        ...

    async def list_by_author(self, author_id: UUID) -> list[BookSummary]:
        """작가가 쓴 책 전 상태 목록 (스튜디오용)."""
        ...

    async def list_published_with_rating(self, rating: str) -> list[BookSummary]:
        """PUBLISHED & 비차단 & 해당 등급인 책 — 사후검토 큐(potato review-queue)용."""
        ...

    async def list_sitemap_entries(self, limit: int = 50000) -> list[tuple[UUID, datetime | None]]:
        """sitemap.xml 용 경량 목록 — 공개된(PUBLISHED·비차단) 책의 (id, published_at)만."""
        ...
