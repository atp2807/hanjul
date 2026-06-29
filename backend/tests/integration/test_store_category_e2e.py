"""스토어 카테고리 탐색 — ?category= 로 장르 필터."""
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

AUTHOR = SocialProfile("GOOGLE", "store-a", "a@x.com", "작가")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", AUTHOR)}, token_issuer())

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_store_filter_by_category(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_auth = {"Authorization": f"Bearer {(await login_account(c, 'google', 'a'))[0]}"}

        async def make(title, category):
            bid = (await c.post("/api/books", json={"title": title}, headers=a_auth)).json()["bookId"]
            await c.put(f"/api/books/{bid}/meta", json={"category": category}, headers=a_auth)
            await c.put(f"/api/books/{bid}/price", json={"amount": 1000}, headers=a_auth)
            await c.post(f"/api/books/{bid}/publish-now", headers=a_auth)

        await make("소설가게책", "소설")
        await make("에세이가게책", "에세이")

        # 전체 — 카테고리 노출
        allb = (await c.get("/api/store/books")).json()["items"]
        by = {x["title"]: x for x in allb}
        assert by["소설가게책"]["category"] == "소설"

        # 카테고리 필터
        only = (await c.get("/api/store/books?category=소설")).json()["items"]
        titles = [x["title"] for x in only]
        assert "소설가게책" in titles and "에세이가게책" not in titles
