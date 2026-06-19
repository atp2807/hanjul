"""작가 스튜디오 E2E — POST /books 작가지정 + GET /me/books (내 책만)."""
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

PROFILE = SocialProfile("GOOGLE", "author-x", "a@x.com", "작가")


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


async def test_my_books_lists_only_my_authored(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}

        assert (await c.get("/api/me/books")).status_code == 401  # 미인증

        mine = (await c.post("/api/books", json={"title": "내 책"}, headers=auth)).json()["bookId"]
        anon = (await c.post("/api/books", json={"title": "익명책"})).json()["bookId"]  # 작가 없음

        books = (await c.get("/api/me/books", headers=auth)).json()
        ids = [b["id"] for b in books["items"]]
        assert mine in ids
        assert anon not in ids


async def test_isbn_set_and_onix_feed(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "내 책"}, headers=auth)).json()["bookId"]

        # 잘못된 ISBN → 422, 유효 ISBN-13 → 204
        assert (await c.put(f"/api/books/{book}/isbn", json={"isbn": "abc"})).status_code == 422
        assert (await c.put(f"/api/books/{book}/isbn", json={"isbn": "9788912345678"})).status_code == 204

        # ONIX 피드에 ISBN·제목·작가(display_name) 반영
        onix = (await c.get(f"/api/books/{book}/onix")).text
        assert "9788912345678" in onix
        assert "<TitleText>내 책</TitleText>" in onix
        assert "<ProductForm>EB</ProductForm>" in onix  # ebook
        assert "작가" in onix  # PROFILE display_name
