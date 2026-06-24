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

    async def update_meta(
        self,
        book_id: UUID,
        subtitle: str | None,
        description: str | None,
        category: str | None,
    ) -> None:
        """부제·소개·분류 일괄 갱신 (빈 문자열은 NULL 로 정규화)."""
        await self._require(book_id)

        def _clean(v: str | None) -> str | None:
            v = v.strip() if v else None
            return v or None

        await self.repo.update_meta(book_id, _clean(subtitle), _clean(description), _clean(category))

    async def submit_for_review(self, book_id: UUID) -> None:
        s = await self._require(book_id)
        if s.status != DRAFT:
            raise InvalidTransition(s.status, REVIEW)
        await self.repo.set_status(book_id, REVIEW)

    async def unpublish(self, book_id: UUID) -> None:
        """출판 취소(비공개) — 스토어에서 내림. PUBLISHED → DRAFT."""
        await self._require(book_id)
        await self.repo.set_status(book_id, DRAFT)

    async def publish(self, book_id: UUID, now: datetime | None = None) -> None:
        s = await self._require(book_id)
        if s.status != REVIEW:
            raise InvalidTransition(s.status, PUBLISHED)
        if s.price_amt is None:
            raise PriceRequired()
        await self.repo.set_status(book_id, PUBLISHED, now or datetime.now(timezone.utc))

    async def auto_publish(self, book_id: UUID, now: datetime | None = None) -> None:
        """즉시 출간 — 심사 단계 생략하고 바로 게시. 가격은 필수."""
        s = await self._require(book_id)
        if s.price_amt is None:
            raise PriceRequired()
        await self.repo.set_status(book_id, PUBLISHED, now or datetime.now(timezone.utc))

    async def schedule_publish(self, book_id: UUID, when: datetime) -> None:
        """예약 발행 — when 시각에 스케줄러가 자동 게시. 가격은 필수."""
        s = await self._require(book_id)
        if s.price_amt is None:
            raise PriceRequired()
        await self.repo.set_scheduled(book_id, when)

    async def publish_scheduled_due(self, now: datetime) -> list[tuple]:
        """예약 시각이 지난 책들 자동 게시 (스케줄러가 호출). 게시된 (id, author_id, title) 목록."""
        return await self.repo.publish_due(now)

    async def list_store(
        self, q: str | None = None, kind: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[BookSummary]:
        return await self.repo.list_published(q, limit, offset, kind)

    async def set_isbn(self, book_id: UUID, isbn: str) -> None:
        await self._require(book_id)
        digits = isbn.replace("-", "").replace(" ", "")
        if not (digits.isdigit() and len(digits) in (10, 13)):
            raise ValueError("ISBN은 10 또는 13자리 숫자여야 합니다")
        await self.repo.set_isbn(book_id, isbn)

    async def set_discount(self, book_id: UUID, amount: int, until) -> None:
        """기간 할인가 설정. 음수 금지. (할인 적용은 주문 시 서버가 도출)"""
        await self._require(book_id)
        if amount < 0:
            raise ValueError("할인가는 0 이상")
        await self.repo.set_discount(book_id, amount, until)

    async def get_meta(self, book_id: UUID) -> BookSummary:
        return await self._require(book_id)

    async def list_published_by_author(self, author_id: UUID) -> list[BookSummary]:
        return await self.repo.list_published_by_author(author_id)

    async def list_my_books(self, author_id: UUID) -> list[BookSummary]:
        return await self.repo.list_by_author(author_id)

    async def get_store_detail(self, book_id: UUID) -> BookSummary:
        s = await self._require(book_id)
        if s.status != PUBLISHED:
            raise BookNotFound(book_id)  # 미출판 책은 스토어에 비공개
        return s
