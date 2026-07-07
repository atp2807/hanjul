"""리뷰 재작성 → updated_ts 갱신('수정됨' 표시 근거). 최초 작성은 NULL."""
import pytest
from fastapi import Depends
from main import app
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_session
from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import SocialProfile
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer

from tests.fixtures.fake_account_repo import FakeProvider
from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book
from tests.integration.order_helpers import buy_book

AUTHOR = SocialProfile("GOOGLE", "rv-author", "a@x.com", "작가")
BUYER = SocialProfile("NAVER", "rv-buyer", "b@x.com", "구매독자")


@pytest.fixture
def app_db(sessionmaker):
    """2-provider(작가·구매독자) 로그인 필요 — conftest의 단일 social_profile app_db로 못 대체."""
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", BUYER)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_rewrite_review_sets_updated_ts(client_orders):
    c = client_orders
    author_token, _ = await login_account(c, "google", "a")
    buyer_token, _ = await login_account(c, "naver", "b")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    buyer_auth = {"Authorization": f"Bearer {buyer_token}"}

    # 출판 + 구매
    book = await create_book(c, author_auth, title="리뷰책")
    await c.put(f"/api/books/{book}/price", json={"amount": 1000}, headers=author_auth)
    await c.post(f"/api/books/{book}/publish-now", headers=author_auth)
    await buy_book(c, buyer_auth, book)

    # 최초 리뷰 → updatedAt NULL
    await c.post(f"/api/books/{book}/reviews", json={"rating": 4, "body": "좋아요"}, headers=buyer_auth)
    item = (await c.get(f"/api/books/{book}/reviews")).json()["items"][0]
    assert item["updatedAt"] is None
    created = item["createdAt"]

    # 재작성 → updatedAt 채워짐, createdAt은 유지
    await c.post(f"/api/books/{book}/reviews", json={"rating": 2, "body": "다시 보니 별로"}, headers=buyer_auth)
    reviews = (await c.get(f"/api/books/{book}/reviews")).json()
    assert reviews["count"] == 1  # 업서트 — 행 안 늘어남
    item2 = reviews["items"][0]
    assert item2["rating"] == 2 and item2["body"] == "다시 보니 별로"
    assert item2["updatedAt"] is not None
    assert item2["createdAt"] == created
