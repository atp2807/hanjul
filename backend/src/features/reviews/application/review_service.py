"""reviews 서비스 — 평점 검증 + 조회."""
from uuid import UUID

from src.features.reviews.domain.models import (
    BookNotFound,
    ReviewRepository,
    ReviewSummary,
    ReviewView,
)
from src.shared.errors import ValidationError


class ReviewService:
    def __init__(self, repo: ReviewRepository):
        self.repo = repo

    async def add(
        self, book_id: UUID, account_id: UUID, rating: int, body: str | None, source_cd: str = "PURCHASE"
    ) -> None:
        if not (1 <= rating <= 5):
            raise ValidationError("평점은 1~5점이어야 해요.")
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        await self.repo.upsert(book_id, account_id, rating, (body or "").strip() or None, source_cd)

    async def list(self, book_id: UUID) -> tuple[ReviewSummary, list[ReviewView]]:
        return await self.repo.summary(book_id), await self.repo.list_for_book(book_id)
