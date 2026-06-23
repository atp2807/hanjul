"""reviews 도메인 — 리뷰 뷰 + 요약 + 리포지토리 포트."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class ReviewView:
    id: UUID
    rating: int
    body: str | None
    author: str | None
    created_at: datetime


@dataclass
class ReviewSummary:
    average: float
    count: int


class ReviewRepository(Protocol):
    async def upsert(self, book_id: UUID, account_id: UUID, rating: int, body: str | None) -> None:
        """(책,계정) 한 건 — 있으면 갱신, 없으면 생성."""
        ...

    async def list_for_book(self, book_id: UUID) -> list[ReviewView]:
        ...

    async def summary(self, book_id: UUID) -> ReviewSummary:
        ...
