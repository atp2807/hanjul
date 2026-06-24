"""서점 배포 E2E — 출판본을 데모 채널로 배포 + 이력."""
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

PROFILE = SocialProfile("GOOGLE", "dist-x", "d@x.com", "작가")


@pytest.fixture
def app_db(sessionmaker):
    settings.DISTRIBUTION_DEMO = True  # 데모 채널 활성

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
    settings.DISTRIBUTION_DEMO = False


async def test_publish_then_distribute_to_store(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}

        # 출판본 준비 (즉시출간)
        book = (await c.post("/api/books", json={"title": "유통책"}, headers=auth)).json()["bookId"]
        await c.post(f"/api/books/{book}/import", json={"rawText": "# 1장\n\n본문"})
        await c.put(f"/api/books/{book}/price", json={"amount": 9000}, headers=auth)
        await c.put(f"/api/books/{book}/isbn", json={"isbn": "9788912345678"}, headers=auth)
        await c.post(f"/api/books/{book}/publish-now", headers=auth)

        # 교보로 배포 (데모) → SENT
        r = await c.post(f"/api/books/{book}/distribute", json={"channel": "KYOBO"})
        assert r.status_code == 201
        body = r.json()
        assert body["statusCd"] == "SENT"
        assert body["channelCd"] == "KYOBO"

        # 이력
        hist = (await c.get(f"/api/books/{book}/distributions")).json()
        assert len(hist) == 1 and hist[0]["channelCd"] == "KYOBO"


async def test_distribute_unpublished_409(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        draft = (await c.post("/api/books", json={"title": "초안"}, headers=auth)).json()["bookId"]
        r = await c.post(f"/api/books/{draft}/distribute", json={"channel": "KYOBO"})
        assert r.status_code == 409  # 출판본만 배포 가능
