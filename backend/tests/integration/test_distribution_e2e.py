"""서점 배포 E2E — 출판본을 데모 채널로 배포 + 이력."""
import pytest
from fastapi import Depends
from main import app
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_session
from src.config.settings import settings
from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import SocialProfile
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer

from tests.fixtures.fake_account_repo import FakeProvider
from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book, import_raw

PROFILE = SocialProfile("GOOGLE", "dist-x", "d@x.com", "작가")
OTHER = SocialProfile("NAVER", "dist-other", "o@x.com", "타인")


@pytest.fixture
def app_db(sessionmaker):
    """2-provider(작가·타인) 로그인 필요 — conftest의 단일 social_profile app_db로 못 대체."""
    settings.DISTRIBUTION_DEMO = True  # 데모 채널 활성

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
    settings.DISTRIBUTION_DEMO = False


async def test_publish_then_distribute_to_store(client):
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}

    # 출판본 준비 (즉시출간)
    book = await create_book(client, auth, title="유통책")
    await import_raw(client, book, "# 1장\n\n본문", auth)
    await client.put(f"/api/books/{book}/price", json={"amount": 9000}, headers=auth)
    await client.put(f"/api/books/{book}/isbn", json={"isbn": "9788912345678"}, headers=auth)
    await client.post(f"/api/books/{book}/publish-now", headers=auth)

    # 인가 게이트 — 무인증 401, 타인 403 (소유 작가만 배포 가능)
    assert (await client.post(f"/api/books/{book}/distribute", json={"channel": "KYOBO"})).status_code == 401
    other_token, _ = await login_account(client, "naver", "y")
    other = {"Authorization": f"Bearer {other_token}"}
    assert (await client.post(f"/api/books/{book}/distribute", json={"channel": "KYOBO"}, headers=other)).status_code == 403

    # 교보로 배포 (데모) → SENT
    r = await client.post(f"/api/books/{book}/distribute", json={"channel": "KYOBO"}, headers=auth)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SENT"
    assert body["channel"] == "KYOBO"

    # 이력 — 역시 소유 작가만 (타인 403)
    assert (await client.get(f"/api/books/{book}/distributions", headers=other)).status_code == 403
    hist = (await client.get(f"/api/books/{book}/distributions", headers=auth)).json()
    assert len(hist) == 1 and hist[0]["channel"] == "KYOBO"


async def test_distribute_unpublished_409(client):
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    draft = await create_book(client, auth, title="초안")
    r = await client.post(f"/api/books/{draft}/distribute", json={"channel": "KYOBO"}, headers=auth)
    assert r.status_code == 409  # 출판본만 배포 가능
