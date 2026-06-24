"""인메모리 ReviewRepository — 서비스 단위 테스트용."""
import uuid
from datetime import datetime, timezone

from src.features.reviews.domain.models import ReviewSummary, ReviewView


class FakeReviewRepository:
    def __init__(self) -> None:
        self.books: set = set()
        self.reviews: dict = {}  # (book_id, account_id) -> (rating, body)

    def seed_book(self, book_id) -> None:
        self.books.add(book_id)

    async def book_exists(self, book_id) -> bool:
        return book_id in self.books

    async def upsert(self, book_id, account_id, rating, body) -> None:
        self.reviews[(book_id, account_id)] = (rating, body)

    async def list_for_book(self, book_id):
        return [
            ReviewView(id=uuid.uuid4(), rating=r, body=b, author="독자", created_at=datetime.now(timezone.utc))
            for (bk, _ac), (r, b) in self.reviews.items()
            if bk == book_id
        ]

    async def summary(self, book_id) -> ReviewSummary:
        rs = [r for (bk, _ac), (r, _b) in self.reviews.items() if bk == book_id]
        return ReviewSummary(average=round(sum(rs) / len(rs), 2) if rs else 0.0, count=len(rs))
