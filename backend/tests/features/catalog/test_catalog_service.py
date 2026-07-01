"""CatalogService — 출판 라이프사이클 규칙 (Fake repo)."""
import uuid

import pytest

from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import (
    BookNotFound,
    BookSummary,
    InvalidTransition,
    PriceRequired,
    DRAFT,
    PUBLISHED,
    REVIEW,
)
from src.shared.errors import ValidationError
from tests.fixtures.fake_catalog_repo import FakeCatalogRepository


def mkbook(status=DRAFT, price=None):
    return BookSummary(
        id=uuid.uuid4(), title="책", subtitle=None, author_id=None,
        kind="BOOK", language="ko", status=status, price_amt=price,
        cover_url=None, published_at=None,
    )


def svc_with(book):
    repo = FakeCatalogRepository()
    repo.seed(book)
    return CatalogService(repo), repo


async def test_submit_moves_draft_to_review():
    book = mkbook(DRAFT)
    svc, repo = svc_with(book)
    await svc.submit_for_review(book.id)
    assert repo.books[book.id].status == REVIEW


async def test_submit_from_non_draft_raises():
    book = mkbook(REVIEW)
    svc, _ = svc_with(book)
    with pytest.raises(InvalidTransition):
        await svc.submit_for_review(book.id)


async def test_publish_requires_review_status():
    book = mkbook(DRAFT, price=1000)
    svc, _ = svc_with(book)
    with pytest.raises(InvalidTransition):
        await svc.publish(book.id)


async def test_publish_requires_price():
    book = mkbook(REVIEW, price=None)
    svc, _ = svc_with(book)
    with pytest.raises(PriceRequired):
        await svc.publish(book.id)


async def test_publish_success_sets_published():
    book = mkbook(REVIEW, price=5000)
    svc, repo = svc_with(book)
    await svc.publish(book.id)
    assert repo.books[book.id].status == PUBLISHED
    assert repo.books[book.id].published_at is not None


async def test_unpublish_moves_published_to_draft():
    book = mkbook(PUBLISHED, price=5000)
    svc, repo = svc_with(book)
    await svc.unpublish(book.id)
    assert repo.books[book.id].status == DRAFT  # 스토어에서 내려감


async def test_set_price_negative_rejected():
    book = mkbook(DRAFT)
    svc, _ = svc_with(book)
    with pytest.raises(ValidationError):
        await svc.set_price(book.id, -100)


async def test_store_detail_hidden_when_unpublished():
    book = mkbook(REVIEW, price=1000)
    svc, _ = svc_with(book)
    with pytest.raises(BookNotFound):
        await svc.get_store_detail(book.id)


async def test_operations_on_missing_book_raise():
    svc, _ = svc_with(mkbook())
    with pytest.raises(BookNotFound):
        await svc.submit_for_review(uuid.uuid4())
