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
        assert (await c.put(f"/api/books/{book}/isbn", json={"isbn": "abc"}, headers=auth)).status_code == 422
        assert (await c.put(f"/api/books/{book}/isbn", json={"isbn": "9788912345678"}, headers=auth)).status_code == 204

        # ONIX 피드에 ISBN·제목·작가(display_name) 반영
        onix = (await c.get(f"/api/books/{book}/onix")).text
        assert "9788912345678" in onix
        assert "<TitleText>내 책</TitleText>" in onix
        assert "<ProductForm>EB</ProductForm>" in onix  # ebook
        assert "작가" in onix  # PROFILE display_name


async def test_import_blocked_for_non_owner(app_db):
    """소유자 있는 책에는 작가 본인만 import — 익명/타인은 403 (남의 책에 장 추가 차단)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "내 원고"}, headers=auth)).json()["bookId"]

        # 무인증 import → 403
        assert (await c.post(f"/api/books/{book}/import", json={"rawText": "탈취"})).status_code == 403
        # 작가 본인 → 200
        assert (await c.post(f"/api/books/{book}/import", json={"rawText": "본문"}, headers=auth)).status_code == 200


async def test_update_meta_reflected_in_store(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "메타책"}, headers=auth)).json()["bookId"]

        r = await c.put(
            f"/api/books/{book}/meta",
            json={"subtitle": "부제다", "description": "한 줄 소개입니다.", "category": "에세이"},
            headers=auth,
        )
        assert r.status_code == 204

        # 빈 문자열은 NULL 로 정규화 (부제 지움)
        await c.put(f"/api/books/{book}/meta", json={"subtitle": "  ", "description": "수정된 소개", "category": "소설"}, headers=auth)

        # /me/books 요약에 반영
        mine = (await c.get("/api/me/books", headers=auth)).json()["items"]
        meta = next(b for b in mine if b["id"] == book)
        assert meta["subtitle"] is None
        assert meta["description"] == "수정된 소개"
        assert meta["category"] == "소설"
