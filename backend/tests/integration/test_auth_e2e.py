"""auth HTTP E2E — 엔드포인트 배선 검증 (Fake provider 주입, 네트워크/DB 없음)."""
import httpx
import pytest

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.application.token import JwtTokenIssuer  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service  # noqa: E402
from tests.fixtures.fake_account_repo import FakeAccountRepository, FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_token  # noqa: E402


@pytest.fixture
def override_auth():
    profile = SocialProfile("GOOGLE", "sub-e2e", "e@x.com", "이용자")
    svc = AuthService(
        FakeAccountRepository(),
        {"GOOGLE": FakeProvider("GOOGLE", profile)},
        JwtTokenIssuer("secret", "HS256", 1),
    )
    app.dependency_overrides[get_auth_service] = lambda: svc
    yield
    app.dependency_overrides.clear()


async def test_login_url_over_http(override_auth):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/google/login?state=abc")
        assert r.status_code == 200
        assert "state=abc" in r.json()["authorizationUrl"]


async def test_callback_redirects_with_token(override_auth):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, is_new = await login_token(c, "google", "xyz")
        assert is_new is True
        assert token  # 프론트로 리다이렉트되며 fragment 에 토큰 실림


async def test_unknown_provider_returns_400(override_auth):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/naver/login")
        assert r.status_code == 400
