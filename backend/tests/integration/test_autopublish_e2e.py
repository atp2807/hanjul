"""자동발행 — 즉시출간(심사 생략) + 예약발행(due 자동 게시)."""
from datetime import UTC, datetime, timedelta

import pytest
from src.features.auth.domain.models import SocialProfile
from src.features.books.infrastructure.book_repo import SqlBookRepository
from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "ap-x", "ap@x.com", "작가")


async def test_publish_now_skips_review(client):
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await create_book(client, auth, title="즉시책")

    # 가격 없이 즉시출간 → 422
    assert (await client.post(f"/api/books/{book}/publish-now", headers=auth)).status_code == 422
    await client.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=auth)
    # 즉시출간 → 204 (DRAFT에서 바로, 심사 생략)
    assert (await client.post(f"/api/books/{book}/publish-now", headers=auth)).status_code == 204
    # 스토어 노출
    store = (await client.get("/api/store/books")).json()
    assert any(i["id"] == book for i in store["items"])


async def test_scheduled_due_is_published(sessionmaker):
    async with sessionmaker() as s:
        bid = await SqlBookRepository(s).create_book(title="예약책", kind="BOOK", language="ko")
        cat = SqlCatalogRepository(s)
        await cat.set_price(bid, 1000)
        await cat.set_scheduled(bid, datetime.now(UTC) - timedelta(hours=1))  # 이미 지남

    async with sessionmaker() as s:
        published = await SqlCatalogRepository(s).publish_due(datetime.now(UTC))
        assert len(published) == 1 and published[0][0] == bid

    async with sessionmaker() as s2:
        summary = await SqlCatalogRepository(s2).get_summary(bid)
        assert summary.status == "PUBLISHED"


async def test_future_scheduled_not_yet_published(sessionmaker):
    async with sessionmaker() as s:
        bid = await SqlBookRepository(s).create_book(title="미래책", kind="BOOK", language="ko")
        cat = SqlCatalogRepository(s)
        await cat.set_price(bid, 1000)
        await cat.set_scheduled(bid, datetime.now(UTC) + timedelta(days=1))  # 미래

    async with sessionmaker() as s:
        assert await SqlCatalogRepository(s).publish_due(datetime.now(UTC)) == []

    async with sessionmaker() as s2:
        assert (await SqlCatalogRepository(s2).get_summary(bid)).status != "PUBLISHED"
