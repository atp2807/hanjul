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


async def test_callback_user_cancel_redirects_with_error(override_auth):
    """사용자가 동의 취소(?error=access_denied) → 422 아니라 #error 리다이렉트."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/google/callback?error=access_denied", follow_redirects=False)
        assert r.status_code == 302
        assert "/auth/callback#error=access_denied" in r.headers["location"]


async def test_callback_no_code_redirects_with_error(override_auth):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/google/callback", follow_redirects=False)
        assert r.status_code == 302
        assert "#error=no_code" in r.headers["location"]


async def test_callback_exchange_failure_redirects_with_error():
    """토큰 교환 실패(redirect_uri_mismatch 등) → 500 아니라 #error=auth_failed."""
    from src.features.auth.application.token import JwtTokenIssuer
    from src.features.auth.domain.models import OAuthExchangeError
    from src.features.auth.presentation.dependencies import get_auth_service

    from tests.fixtures.fake_account_repo import FakeAccountRepository

    class BoomProvider:
        provider_cd = "GOOGLE"
        def authorization_url(self, state):
            return "https://fake"
        async def exchange(self, code):
            raise OAuthExchangeError("token exchange 400: redirect_uri_mismatch")

    svc = AuthService(FakeAccountRepository(), {"GOOGLE": BoomProvider()}, JwtTokenIssuer("s", "HS256", 1))
    app.dependency_overrides[get_auth_service] = lambda: svc
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/auth/google/callback?code=badcode", follow_redirects=False)
            assert r.status_code == 302
            assert "#error=auth_failed" in r.headers["location"]
    finally:
        app.dependency_overrides.clear()


async def test_unknown_provider_returns_400(override_auth):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/naver/login")
        assert r.status_code == 400


async def test_test_login_blocked_by_default(override_auth):
    # fail-closed: 플래그 꺼져 있으면 404
    settings.E2E_LOGIN_ENABLED = False
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/test-login?email=e2e@x.com")
        assert r.status_code == 404


async def test_test_login_issues_token_when_enabled(override_auth):
    settings.E2E_LOGIN_ENABLED = True
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/auth/test-login?email=e2e@x.com&name=작가", follow_redirects=False)
            assert r.status_code == 302
            assert "/auth/callback#token=" in r.headers["location"]
    finally:
        settings.E2E_LOGIN_ENABLED = False
