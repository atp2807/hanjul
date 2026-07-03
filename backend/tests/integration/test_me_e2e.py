"""인증 컨텍스트 E2E — 로그인 → 토큰 → GET /me."""
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
from tests.integration.auth_helpers import login_token  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "me-sub", "me@x.com", "나")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        # 토큰 발급 issuer 는 get_current_account 와 같은 settings 시크릿을 써야 검증됨
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", PROFILE)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_me_requires_token_and_returns_account(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        # 미로그인 → 401
        assert (await c.get("/api/me")).status_code == 401
        # 잘못된 토큰 → 401
        assert (await c.get("/api/me", headers={"Authorization": "Bearer garbage"})).status_code == 401

        # 로그인 → 토큰 → /me
        token, _ = await login_token(c, "google", "x")
        r = await c.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "me@x.com"
        assert body["role"] == "READER"
