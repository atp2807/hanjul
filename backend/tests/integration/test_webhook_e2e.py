"""토스 웹훅 E2E — 대시보드 취소 → reconcile 환불. 바디 불신(PG 재조회로만)."""
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

AUTHOR = SocialProfile("GOOGLE", "wh-a", "a@x.com", "작가")
BUYER = SocialProfile("NAVER", "wh-b", "b@x.com", "독자")


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


async def _paid_order(c):
    author_token, _ = await login_account(c, "google", "a")
    a_auth = {"Authorization": f"Bearer {author_token}"}
    book = await create_book(c, a_auth, title="웹훅책")
    await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
    await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
    buyer_token, _ = await login_account(c, "naver", "b")
    b_auth = {"Authorization": f"Bearer {buyer_token}"}
    oid = await buy_book(c, b_auth, book)
    return oid, b_auth


async def test_webhook_cancel_reconciles_to_refunded(client_orders, order_gateway):
    c = client_orders
    oid, b_auth = await _paid_order(c)
    assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).json()["status"] == "PAID"

    # PG가 취소 상태로 보고 → 웹훅 reconcile → 환불
    order_gateway.status = "CANCELED"
    r = await c.post("/api/payments/webhook", json={"data": {"orderId": oid, "status": "CANCELED"}})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).json()["status"] == "REFUNDED"


async def test_webhook_body_not_trusted(client_orders, order_gateway):
    """바디가 CANCELED라 주장해도 PG 실제 상태가 DONE이면 환불 안 함(위조 방어)."""
    c = client_orders
    oid, b_auth = await _paid_order(c)
    order_gateway.status = "DONE"  # PG는 정상 결제로 보고
    await c.post("/api/payments/webhook", json={"data": {"orderId": oid, "status": "CANCELED"}})
    assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).json()["status"] == "PAID"


async def test_webhook_unknown_order_still_200(client_orders):
    import uuid

    c = client_orders
    r = await c.post("/api/payments/webhook", json={"orderId": str(uuid.uuid4())})
    assert r.status_code == 200
    r2 = await c.post("/api/payments/webhook", json={"garbage": True})
    assert r2.status_code == 200
