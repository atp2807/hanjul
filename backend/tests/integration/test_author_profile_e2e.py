"""작가 공개 프로필 E2E — bio 설정 + /authors/{id}(이름·소개·출판작)."""
import uuid

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

PROFILE = SocialProfile("GOOGLE", "auth-prof", "a@x.com", "작가한")


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


async def test_author_profile_bio_and_published_books(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        author_id = (await c.get("/api/me", headers=auth)).json()["id"]

        # bio 설정
        assert (await c.put("/api/me/profile", json={"bio": "소설 쓰는 사람"}, headers=auth)).status_code == 204

        # 출판작 1
        book = (await c.post("/api/books", json={"title": "내 소설"}, headers=auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=auth)
        await c.post(f"/api/books/{book}/publish-now", headers=auth)

        # 공개 프로필
        prof = (await c.get(f"/api/authors/{author_id}")).json()
        assert prof["displayName"] == "작가한"
        assert prof["bio"] == "소설 쓰는 사람"
        assert any(b["id"] == book for b in prof["books"])

        # 없는 작가 404
        assert (await c.get(f"/api/authors/{uuid.uuid4()}")).status_code == 404
