"""리뷰·평점 E2E — 작성(로그인)/조회/검증/업서트."""
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
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "rv", "r@x.com", "독자김")


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


async def test_review_add_list_validate_upsert(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "리뷰책"}, headers=auth)).json()["bookId"]

        # 미로그인 작성 거부
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5})).status_code == 401
        # 잘못된 평점 422
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 6}, headers=auth)).status_code == 422
        # 없는 책 404 (ghost 리뷰 방지)
        import uuid as _uuid
        assert (await c.post(f"/api/books/{_uuid.uuid4()}/reviews", json={"rating": 5}, headers=auth)).status_code == 404

        # 작성 → 201
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 4, "body": "좋아요"}, headers=auth)).status_code == 201

        r = (await c.get(f"/api/books/{book}/reviews")).json()
        assert r["average"] == 4.0 and r["count"] == 1
        assert r["items"][0]["rating"] == 4 and r["items"][0]["author"] == "독자김"

        # 같은 사용자 재작성 → 업서트(갱신, 중복 아님)
        await c.post(f"/api/books/{book}/reviews", json={"rating": 2, "body": "별로"}, headers=auth)
        r2 = (await c.get(f"/api/books/{book}/reviews")).json()
        assert r2["count"] == 1 and r2["average"] == 2.0
