"""reviews 도메인 — 리뷰 뷰 + 요약 + 리포지토리 포트."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.errors import NotFoundError


@dataclass
class ReviewView:
    id: UUID
    rating: int
    body: str | None
    account_id: UUID  # 작성자 — 이름은 합성루트(엔드포인트)가 accounts.names_for로 해석
    created_at: datetime
    updated_at: datetime | None = None
    source_cd: str = "PURCHASE"  # PURCHASE | REVIEW_COPY(서평단)


@dataclass
class ReviewSummary:
    average: float
    count: int


class BookNotFound(NotFoundError):
    """리뷰 대상 책 없음 → 404."""

    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("책을 찾을 수 없어요.")


class ReviewRepository(Protocol):
    async def book_exists(self, book_id: UUID) -> bool:
        ...

    async def upsert(
        self, book_id: UUID, account_id: UUID, rating: int, body: str | None, source_cd: str = "PURCHASE"
    ) -> None:
        """(책,계정) 한 건 — 있으면 갱신, 없으면 생성. source_cd=리뷰 출처."""
        ...

    async def list_for_book(self, book_id: UUID) -> list[ReviewView]:
        ...

    async def summary(self, book_id: UUID) -> ReviewSummary:
        ...
