"""책 삭제 E2E — 작가가 자기 책 삭제. 판매 이력 있으면 차단."""
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

AUTHOR = SocialProfile("GOOGLE", "del-a", "a@x.com", "작가")
BUYER = SocialProfile("NAVER", "del-b", "b@x.com", "독자")


@pytest.fixture
def app_db(sessionmaker):
    """두 provider(작가·독자) 동시 로그인이 필요 — conftest의 단일 social_profile app_db로 못 대체."""
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


async def test_author_deletes_draft_book(client):
    a_token, _ = await login_account(client, "google", "a")
    a_auth = {"Authorization": f"Bearer {a_token}"}
    book = await create_book(client, a_auth, title="삭제할초안")

    assert (await client.delete(f"/api/books/{book}", headers=a_auth)).status_code == 204
    # /me/books 에서 사라짐
    mine = (await client.get("/api/me/books", headers=a_auth)).json()["items"]
    assert all(b["id"] != book for b in mine)


async def test_non_owner_cannot_delete(client):
    a_token, _ = await login_account(client, "google", "a")
    b_token, _ = await login_account(client, "naver", "b")
    book = await create_book(client, {"Authorization": f"Bearer {a_token}"}, title="남의책")

    assert (await client.delete(f"/api/books/{book}", headers={"Authorization": f"Bearer {b_token}"})).status_code == 403


async def test_cannot_delete_sold_book(client_orders):
    a_token, _ = await login_account(client_orders, "google", "a")
    b_token, _ = await login_account(client_orders, "naver", "b")
    a_auth = {"Authorization": f"Bearer {a_token}"}
    b_auth = {"Authorization": f"Bearer {b_token}"}
    book = await create_book(client_orders, a_auth, title="팔린책")
    await client_orders.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
    await client_orders.post(f"/api/books/{book}/publish-now", headers=a_auth)
    # 독자가 구매(주문 생성) → 판매 이력
    await client_orders.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=b_auth)

    # 판매 이력 있으니 삭제 차단(409)
    assert (await client_orders.delete(f"/api/books/{book}", headers=a_auth)).status_code == 409
