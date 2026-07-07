"""표지 직접 업로드 E2E — 작가가 이미지 올려 책 표지 설정."""
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
from src.features.cover.application.cover_service import CoverService  # noqa: E402
from src.features.cover.infrastructure.cover_repo import SqlCoverRepository  # noqa: E402
from src.features.cover.presentation.dependencies import get_cover_service  # noqa: E402

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_cover import FakeCoverGenerator, FakeCoverStorage  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "cov-a", "a@x.com", "작가")
OTHER = SocialProfile("NAVER", "cov-o", "o@x.com", "남")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # 최소 PNG 시그니처


@pytest.fixture
def app_db(sessionmaker):
    storage = FakeCoverStorage()

    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", OTHER)},
            token_issuer(),
        )

    def _cover(session: AsyncSession = Depends(get_session)):
        return CoverService(SqlCoverRepository(session), FakeCoverGenerator(), storage)

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_cover_service] = _cover
    yield storage
    app.dependency_overrides.clear()


async def test_author_uploads_cover(app_db):
    storage = app_db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_token, _ = await login_account(c, "google", "a")
        a_auth = {"Authorization": f"Bearer {a_token}"}
        book = (await c.post("/api/books", json={"title": "표지업로드책"}, headers=a_auth)).json()["bookId"]

        r = await c.post(
            f"/api/books/{book}/cover/upload",
            files={"file": ("my_cover.png", PNG, "image/png")},
            headers=a_auth,
        )
        assert r.status_code == 200, r.text
        url = r.json()["coverUrl"]
        assert url.endswith(".png") and storage.saved  # 저장소에 저장됨

        # 책에 연결 → /me/books 반영
        mine = (await c.get("/api/me/books", headers=a_auth)).json()["items"]
        assert next(b for b in mine if b["id"] == book)["coverUrl"] == url


async def test_non_owner_cannot_upload(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_token, _ = await login_account(c, "google", "a")
        o_token, _ = await login_account(c, "naver", "o")
        book = (await c.post("/api/books", json={"title": "남의책"}, headers={"Authorization": f"Bearer {a_token}"})).json()["bookId"]

        r = await c.post(
            f"/api/books/{book}/cover/upload",
            files={"file": ("x.png", PNG, "image/png")},
            headers={"Authorization": f"Bearer {o_token}"},
        )
        assert r.status_code == 403


async def test_rejects_non_image(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_token, _ = await login_account(c, "google", "a")
        a_auth = {"Authorization": f"Bearer {a_token}"}
        book = (await c.post("/api/books", json={"title": "비이미지"}, headers=a_auth)).json()["bookId"]

        r = await c.post(
            f"/api/books/{book}/cover/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
            headers=a_auth,
        )
        assert r.status_code == 422
