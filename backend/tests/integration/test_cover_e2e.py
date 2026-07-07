"""표지 생성 E2E — 데모 게이트로 오프라인 생성 + 책 연결, 미설정 시 503."""
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

PROFILE = SocialProfile("GOOGLE", "cover-x", "c@x.com", "작가")
OTHER = SocialProfile("NAVER", "cover-other", "o@x.com", "타인")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", PROFILE), "NAVER": FakeProvider("NAVER", OTHER)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()
    settings.COVER_DEMO = False


async def test_demo_cover_generated_and_linked(app_db):
    settings.COVER_DEMO = True
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "표지책"}, headers=auth)).json()["bookId"]

        # 인가 게이트 — 무인증 401, 타인 403 (소유 작가만 생성 가능)
        assert (await c.post(f"/api/books/{book}/cover", json={"prompt": "x"})).status_code == 401
        other_token, _ = await login_account(c, "naver", "y")
        other = {"Authorization": f"Bearer {other_token}"}
        assert (await c.post(f"/api/books/{book}/cover", json={"prompt": "x"}, headers=other)).status_code == 403

        r = await c.post(f"/api/books/{book}/cover", json={"prompt": "잔잔한 한국 에세이"}, headers=auth)
        assert r.status_code == 200
        url = r.json()["coverUrl"]
        assert url.startswith("data:image/svg+xml")

        # 책에 연결돼 /me/books 요약에 반영
        mine = (await c.get("/api/me/books", headers=auth)).json()["items"]
        assert next(b for b in mine if b["id"] == book)["coverUrl"] == url


async def test_cover_unconfigured_returns_503(app_db):
    settings.COVER_DEMO = False  # 데모 끔 + COVER_API_URL 비어있음
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "표지책2"}, headers=auth)).json()["bookId"]
        r = await c.post(f"/api/books/{book}/cover", json={"prompt": "x"}, headers=auth)
        assert r.status_code == 503
