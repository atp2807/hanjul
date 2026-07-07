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


async def test_review_gates(app_db):
    """작성 게이트: 미로그인 401 / 없는 책 404 / 미구매 403 (구매자만 리뷰)."""
    import uuid as _uuid

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "리뷰책"}, headers=auth)).json()["bookId"]

        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5})).status_code == 401
        assert (await c.post(f"/api/books/{_uuid.uuid4()}/reviews", json={"rating": 5}, headers=auth)).status_code == 404
        # 작가 본인도 구매 안 했으면 리뷰 불가(자기책 셀프리뷰 방지)
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5}, headers=auth)).status_code == 403
