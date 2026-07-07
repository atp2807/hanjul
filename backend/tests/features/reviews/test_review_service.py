"""ReviewService 단위 — 평점 검증·book_exists·요약 (Fake repo)."""
import uuid

import pytest
from src.features.reviews.application.review_service import ReviewService
from src.features.reviews.domain.models import BookNotFound
from src.shared.errors import ValidationError

from tests.fixtures.fake_review_repo import FakeReviewRepository


async def test_add_validates_rating_range():
    repo = FakeReviewRepository()
    book = uuid.uuid4()
    repo.seed_book(book)
    svc = ReviewService(repo)
    for bad in (0, 6, -1):
        with pytest.raises(ValidationError):
            await svc.add(book, uuid.uuid4(), bad, None)


async def test_add_unknown_book_raises():
    with pytest.raises(BookNotFound):
        await ReviewService(FakeReviewRepository()).add(uuid.uuid4(), uuid.uuid4(), 5, None)


async def test_add_then_summary_and_list():
    repo = FakeReviewRepository()
    book = uuid.uuid4()
    repo.seed_book(book)
    svc = ReviewService(repo)
    await svc.add(book, uuid.uuid4(), 4, "좋아요")
    await svc.add(book, uuid.uuid4(), 2, "  ")  # 공백 본문 → None
    summary, items = await svc.list(book)
    assert summary.count == 2 and summary.average == 3.0
    assert {i.rating for i in items} == {4, 2}
    assert any(i.body is None for i in items)  # 공백 정규화
