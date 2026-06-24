"""작가 매출/정산 요약 E2E — 작가 출판 → 독자 구매 → GET /me/sales."""
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

AUTHOR = SocialProfile("GOOGLE", "author-s", "au@x.com", "작가")
BUYER = SocialProfile("NAVER", "buyer-s", "bu@x.com", "독자")


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


async def test_author_sales_summary(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        # 작가: 출판본(가격 10000)
        author_token, _ = await login_account(c, "google", "a")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        book_id = (await c.post("/api/books", json={"title": "내 책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book_id}/price", json={"amount": 10000}, headers=a_auth)
        await c.post(f"/api/books/{book_id}/submit", headers=a_auth)
        await c.post(f"/api/books/{book_id}/publish", headers=a_auth)

        # 처음엔 매출 0
        empty = (await c.get("/api/me/sales", headers=a_auth)).json()
        assert empty["totalOrders"] == 0 and empty["totalRevenue"] == 0

        # 독자: 구매
        buyer_token, _ = await login_account(c, "naver", "b")
        b_auth = {"Authorization": f"Bearer {buyer_token}"}
        oid = (await c.post("/api/orders", json={"bookId": book_id}, headers=b_auth)).json()["id"]
        await c.post(f"/api/orders/{oid}/confirm", json={"pgTxId": "tx"}, headers=b_auth)

        # 작가 매출 요약
        sales = (await c.get("/api/me/sales", headers=a_auth)).json()
        assert sales["totalOrders"] == 1
        assert sales["totalRevenue"] == 10000
        assert sales["totalPayout"] == 6769  # 자체 70% - 3.3% 원천
        assert sales["books"][0]["bookId"] == book_id
        assert sales["books"][0]["payout"] == 6769

        assert (await c.get("/api/me/sales")).status_code == 401  # 미인증


async def test_buyer_has_no_author_sales(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        buyer_token, _ = await login_account(c, "naver", "b")
        sales = (await c.get("/api/me/sales", headers={"Authorization": f"Bearer {buyer_token}"})).json()
        assert sales["totalRevenue"] == 0 and sales["books"] == []


async def test_order_visible_only_to_buyer(app_db):
    """주문 조회는 본인만 — 타인/무인증은 404 (정보 노출 차단)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        book = (await c.post("/api/books", json={"title": "책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)

        buyer_token, _ = await login_account(c, "naver", "b")
        b_auth = {"Authorization": f"Bearer {buyer_token}"}
        oid = (await c.post("/api/orders", json={"bookId": book}, headers=b_auth)).json()["id"]

        assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).status_code == 200  # 본인
        assert (await c.get(f"/api/orders/{oid}", headers=a_auth)).status_code == 404  # 타인
        assert (await c.get(f"/api/orders/{oid}")).status_code == 401  # 무인증
