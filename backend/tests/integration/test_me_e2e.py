"""인증 컨텍스트 E2E — 로그인 → 토큰 → GET /me."""
import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_token


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "me-sub", "me@x.com", "나")


async def test_me_requires_token_and_returns_account(client):
    # 미로그인 → 401
    assert (await client.get("/api/me")).status_code == 401
    # 잘못된 토큰 → 401
    assert (await client.get("/api/me", headers={"Authorization": "Bearer garbage"})).status_code == 401

    # 로그인 → 토큰 → /me
    token, _ = await login_token(client, "google", "x")
    r = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "me@x.com"
    assert body["role"] == "READER"
