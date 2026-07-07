"""auth HTTP E2E — 엔드포인트 배선 검증 (Fake provider 주입, 네트워크/DB 없음)."""
from urllib.parse import parse_qs, urlparse

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


# ── 데스크탑 루프백 next (한줄 IDE P1 슬라이스5, RFC 8252) ────────────────────


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example.com/callback",  # 외부 호스트
        "http://localhost:53219/callback",  # localhost 표기(리터럴 127.0.0.1만 허용)
        "http://127.0.0.1:53219/other",  # 경로 변형(/callback 아님)
    ],
)
async def test_login_rejects_disallowed_next(override_auth, next_url):
    """allowlist 밖 next는 조용히 기본값으로 대체하지 않고 422로 알린다(open redirect 방지)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/auth/google/login", params={"next": next_url})
        assert r.status_code == 422, r.text


async def test_login_allows_loopback_next(override_auth):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(
            "/api/auth/google/login", params={"next": "http://127.0.0.1:53219/callback"}
        )
        assert r.status_code == 200


async def test_callback_with_loopback_next_redirects_via_query_token(override_auth):
    """state 왕복 — /login이 실은 next가 callback까지 살아남아 fragment 대신 쿼리스트링으로
    토큰을 전달한다(루프백 리스너는 순수 HTTP 서버라 fragment를 못 받는다)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        next_url = "http://127.0.0.1:53219/callback"
        login_res = await c.get("/api/auth/google/login", params={"next": next_url})
        assert login_res.status_code == 200
        # FakeProvider.authorization_url은 "https://fake/auth?state={state}"를 그대로 반환
        # (urlencode 없음) — state 값만 그대로 꺼내 callback에 되돌려준다(Google 왕복 시뮬레이션).
        auth_url = login_res.json()["authorizationUrl"]
        state_value = auth_url.split("state=", 1)[1]

        cb = await c.get(
            "/api/auth/google/callback",
            params={"code": "xyz", "state": state_value},
            follow_redirects=False,
        )
        assert cb.status_code == 302
        location = cb.headers["location"]
        assert location.startswith(f"{next_url}?"), location
        assert "#" not in location  # fragment 아니라 쿼리스트링
        params = parse_qs(urlparse(location).query)
        assert params["token"][0]
        assert params["isNew"][0] == "1"


async def test_callback_ignores_tampered_next_in_state(override_auth):
    """/login을 거치지 않고 state를 직접 조작해 callback에 도달해도(allowlist 우회 시도)
    위조 next로 토큰이 새지 않고 기존 웹 fragment 플로우로 안전하게 폴백한다(이중 검증)."""
    import json

    forged_state = "dnext:" + json.dumps({"s": "", "next": "https://evil.example.com/steal"})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(
            "/api/auth/google/callback",
            params={"code": "xyz", "state": forged_state},
            follow_redirects=False,
        )
        assert r.status_code == 302
        location = r.headers["location"]
        assert location.startswith(f"{settings.FRONTEND_URL}/auth/callback#")
        assert "evil.example.com" not in location


async def test_test_login_with_loopback_next_uses_query_token(override_auth):
    """test-login(E2E 우회)도 next를 지원 — 데스크탑 개발 시 실 Google 자격증명 없이
    루프백 플로우를 손으로 확인할 수 있게(desktop/README.md 절차)."""
    settings.E2E_LOGIN_ENABLED = True
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(
                "/api/auth/test-login",
                params={"email": "desk@x.com", "next": "http://127.0.0.1:53219/callback"},
                follow_redirects=False,
            )
            assert r.status_code == 302
            assert r.headers["location"].startswith("http://127.0.0.1:53219/callback?token=")
    finally:
        settings.E2E_LOGIN_ENABLED = False
