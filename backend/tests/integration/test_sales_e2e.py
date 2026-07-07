"""작가 매출/정산 요약 E2E — 작가 출판 → 독자 구매 → GET /me/sales."""
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
from tests.integration.book_helpers import create_book, import_raw
from tests.integration.order_helpers import buy_book

AUTHOR = SocialProfile("GOOGLE", "author-s", "au@x.com", "작가")
BUYER = SocialProfile("NAVER", "buyer-s", "bu@x.com", "독자")


@pytest.fixture
def app_db(sessionmaker):
    """2-provider(작가·독자) 로그인 필요 — conftest의 단일 social_profile app_db로 못 대체."""
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


async def test_author_sales_summary(client_orders):
    c = client_orders
    # 작가: 출판본(가격 10000)
    author_token, _ = await login_account(c, "google", "a")
    a_auth = {"Authorization": f"Bearer {author_token}"}
    book_id = await create_book(c, a_auth, title="내 책")
    await c.put(f"/api/books/{book_id}/price", json={"amount": 10000}, headers=a_auth)
    await c.post(f"/api/books/{book_id}/submit", headers=a_auth)
    await c.post(f"/api/books/{book_id}/publish", headers=a_auth)

    # 처음엔 매출 0
    empty = (await c.get("/api/me/sales", headers=a_auth)).json()
    assert empty["totalOrders"] == 0 and empty["totalRevenue"] == 0

    # 독자: 구매
    buyer_token, _ = await login_account(c, "naver", "b")
    b_auth = {"Authorization": f"Bearer {buyer_token}"}
    await buy_book(c, b_auth, book_id)

    # 작가 매출 요약
    sales = (await c.get("/api/me/sales", headers=a_auth)).json()
    assert sales["totalOrders"] == 1
    assert sales["totalRevenue"] == 10000
    assert sales["totalPayout"] == 6769  # 자체 70% - 3.3% 원천
    assert sales["books"][0]["bookId"] == book_id
    assert sales["books"][0]["payout"] == 6769

    assert (await c.get("/api/me/sales")).status_code == 401  # 미인증


async def test_buyer_has_no_author_sales(client_orders):
    c = client_orders
    buyer_token, _ = await login_account(c, "naver", "b")
    sales = (await c.get("/api/me/sales", headers={"Authorization": f"Bearer {buyer_token}"})).json()
    assert sales["totalRevenue"] == 0 and sales["books"] == []


async def test_refund_revokes_access_and_sales(client_orders):
    """환불 → 서재 권한 회수 + 작가 매출에서 제외 + 재환불 409."""
    c = client_orders
    author_token, _ = await login_account(c, "google", "a")
    a_auth = {"Authorization": f"Bearer {author_token}"}
    book = await create_book(c, a_auth, title="환불책")
    await import_raw(c, book, "1\n\n2\n\n3", a_auth)
    await c.put(f"/api/books/{book}/price", json={"amount": 8000}, headers=a_auth)
    await c.post(f"/api/books/{book}/publish-now", headers=a_auth)

    buyer_token, _ = await login_account(c, "naver", "b")
    b_auth = {"Authorization": f"Bearer {buyer_token}"}
    oid = await buy_book(c, b_auth, book)

    # 구매 직후: 전체 열람 + 작가 매출 1건
    assert (await c.get(f"/api/books/{book}/content", headers=b_auth)).json()["isPreview"] is False
    assert (await c.get("/api/me/sales", headers=a_auth)).json()["totalOrders"] == 1

    # 타인 환불 시도 → 404 (소유 아님)
    assert (await c.post(f"/api/orders/{oid}/refund", headers=a_auth)).status_code == 404
    # 본인 환불 → 204
    assert (await c.post(f"/api/orders/{oid}/refund", headers=b_auth)).status_code == 204

    # 환불 후: 미리보기로 회귀 + 매출 0 + 재환불 409
    assert (await c.get(f"/api/books/{book}/content", headers=b_auth)).json()["isPreview"] is True
    assert (await c.get("/api/me/sales", headers=a_auth)).json()["totalOrders"] == 0
    assert (await c.post(f"/api/orders/{oid}/refund", headers=b_auth)).status_code == 409


async def test_order_visible_only_to_buyer(client_orders):
    """주문 조회는 본인만 — 타인/무인증은 404 (정보 노출 차단)."""
    c = client_orders
    author_token, _ = await login_account(c, "google", "a")
    a_auth = {"Authorization": f"Bearer {author_token}"}
    book = await create_book(c, a_auth, title="책")
    await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
    await c.post(f"/api/books/{book}/publish-now", headers=a_auth)

    buyer_token, _ = await login_account(c, "naver", "b")
    b_auth = {"Authorization": f"Bearer {buyer_token}"}
    oid = (await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=b_auth)).json()["id"]

    assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).status_code == 200  # 본인
    assert (await c.get(f"/api/orders/{oid}", headers=a_auth)).status_code == 404  # 타인
    assert (await c.get(f"/api/orders/{oid}")).status_code == 401  # 무인증
