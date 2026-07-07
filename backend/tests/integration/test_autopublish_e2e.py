"""자동발행 — 즉시출간(심사 생략) + 예약발행(due 자동 게시)."""
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.features.books.infrastructure.book_repo import SqlBookRepository  # noqa: E402
from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository  # noqa: E402

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "ap-x", "ap@x.com", "작가")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", PROFILE)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_publish_now_skips_review(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "즉시책"}, headers=auth)).json()["bookId"]

        # 가격 없이 즉시출간 → 422
        assert (await c.post(f"/api/books/{book}/publish-now", headers=auth)).status_code == 422
        await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=auth)
        # 즉시출간 → 204 (DRAFT에서 바로, 심사 생략)
        assert (await c.post(f"/api/books/{book}/publish-now", headers=auth)).status_code == 204
        # 스토어 노출
        store = (await c.get("/api/store/books")).json()
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
