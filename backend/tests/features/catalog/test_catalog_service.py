"""CatalogService — 출판 라이프사이클 규칙 (Fake repo)."""
import uuid

import pytest
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import (
    DRAFT,
    PUBLISHED,
    REVIEW,
    BookNotFound,
    BookSummary,
    InvalidTransition,
    PriceRequired,
)
from src.shared.errors import ValidationError

from tests.fixtures.fake_catalog_repo import FakeCatalogRepository
from tests.fixtures.fake_order_repo import FakeAccountTier


def mkbook(status=DRAFT, price=None, content_rating="ALL"):
    return BookSummary(
        id=uuid.uuid4(), title="책", subtitle=None, author_id=None,
        kind="BOOK", language="ko", status=status, price_amt=price,
        cover_url=None, published_at=None, content_rating=content_rating,
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


# ── 연령 게이트(dc-daeb0d3d) — 스토어 목록 필터링 ────────
async def test_list_store_no_account_tier_port_still_hides_restricted_book():
    """account_tier 미주입(기본값)이어도 tier가 "ALL"로 간주돼 등급있는 책은 여전히 숨는다.

    (ALL 등급 책만 있는 기존 Fake 테스트는 이 fail-closed 기본값의 영향을 받지 않는다.)
    """
    repo = FakeCatalogRepository()
    repo.seed(mkbook(status=PUBLISHED, price=1000, content_rating="AGE18"))
    svc = CatalogService(repo)

    items = await svc.list_store()
    assert items == []


async def test_list_store_no_account_tier_port_shows_all_rated_book():
    repo = FakeCatalogRepository()
    book = mkbook(status=PUBLISHED, price=1000, content_rating="ALL")
    repo.seed(book)
    svc = CatalogService(repo)

    items = await svc.list_store()
    assert [b.id for b in items] == [book.id]


async def test_list_store_hides_restricted_book_for_unverified_account():
    repo = FakeCatalogRepository()
    all_book = mkbook(status=PUBLISHED, price=1000, content_rating="ALL")
    age18_book = mkbook(status=PUBLISHED, price=1000, content_rating="AGE18")
    repo.seed(all_book)
    repo.seed(age18_book)
    svc = CatalogService(repo, account_tier=FakeAccountTier())

    items = await svc.list_store()  # account_id 없음(비로그인) → ALL만
    assert {b.id for b in items} == {all_book.id}


async def test_list_store_shows_restricted_book_for_verified_account():
    repo = FakeCatalogRepository()
    all_book = mkbook(status=PUBLISHED, price=1000, content_rating="ALL")
    age18_book = mkbook(status=PUBLISHED, price=1000, content_rating="AGE18")
    repo.seed(all_book)
    repo.seed(age18_book)
    account_id = uuid.uuid4()
    svc = CatalogService(repo, account_tier=FakeAccountTier({account_id: "AGE18"}))

    items = await svc.list_store(account_id=account_id)
    assert {b.id for b in items} == {all_book.id, age18_book.id}
