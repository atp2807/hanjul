"""reviews 서비스 — 평점 검증 + 조회."""
from uuid import UUID

from src.features.reviews.domain.models import ReviewRepository, ReviewSummary, ReviewView


class ReviewService:
    def __init__(self, repo: ReviewRepository):
        self.repo = repo

    async def add(self, book_id: UUID, account_id: UUID, rating: int, body: str | None) -> None:
        if not (1 <= rating <= 5):
            raise ValueError("평점은 1~5")
        await self.repo.upsert(book_id, account_id, rating, (body or "").strip() or None)

    async def list(self, book_id: UUID) -> tuple[ReviewSummary, list[ReviewView]]:
        return await self.repo.summary(book_id), await self.repo.list_for_book(book_id)
