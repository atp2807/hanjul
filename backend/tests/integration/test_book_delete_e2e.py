"""책 삭제 E2E — 작가가 자기 책 삭제. 판매 이력 있으면 차단."""
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
from src.features.billing.application.order_service import OrderService  # noqa: E402
from src.features.billing.infrastructure.book_pricing import SqlBookPricing  # noqa: E402
from src.features.billing.infrastructure.order_repo import SqlOrderRepository  # noqa: E402
from src.features.billing.presentation.dependencies import get_order_service  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.fake_order_repo import FakeGateway  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "del-a", "a@x.com", "작가")
BUYER = SocialProfile("NAVER", "del-b", "b@x.com", "독자")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", BUYER)},
            token_issuer(),
        )

    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


async def test_author_deletes_draft_book(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_token, _ = await login_account(c, "google", "a")
        a_auth = {"Authorization": f"Bearer {a_token}"}
        book = (await c.post("/api/books", json={"title": "삭제할초안"}, headers=a_auth)).json()["bookId"]

        assert (await c.delete(f"/api/books/{book}", headers=a_auth)).status_code == 204
        # /me/books 에서 사라짐
        mine = (await c.get("/api/me/books", headers=a_auth)).json()["items"]
        assert all(b["id"] != book for b in mine)


async def test_non_owner_cannot_delete(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_token, _ = await login_account(c, "google", "a")
        b_token, _ = await login_account(c, "naver", "b")
        book = (await c.post("/api/books", json={"title": "남의책"}, headers={"Authorization": f"Bearer {a_token}"})).json()["bookId"]

        assert (await c.delete(f"/api/books/{book}", headers={"Authorization": f"Bearer {b_token}"})).status_code == 403


async def test_cannot_delete_sold_book(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        a_token, _ = await login_account(c, "google", "a")
        b_token, _ = await login_account(c, "naver", "b")
        a_auth = {"Authorization": f"Bearer {a_token}"}
        b_auth = {"Authorization": f"Bearer {b_token}"}
        book = (await c.post("/api/books", json={"title": "팔린책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
        # 독자가 구매(주문 생성) → 판매 이력
        await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=b_auth)

        # 판매 이력 있으니 삭제 차단(409)
        assert (await c.delete(f"/api/books/{book}", headers=a_auth)).status_code == 409
