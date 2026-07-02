"""토스 웹훅 E2E — 대시보드 취소 → reconcile 환불. 바디 불신(PG 재조회로만)."""
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

AUTHOR = SocialProfile("GOOGLE", "wh-a", "a@x.com", "작가")
BUYER = SocialProfile("NAVER", "wh-b", "b@x.com", "독자")

GATEWAY = FakeGateway(ok=True)  # .status 를 테스트에서 조작


@pytest.fixture
def app_db(sessionmaker):
    GATEWAY.status = None

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
        return OrderService(SqlOrderRepository(session), GATEWAY, SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


async def _paid_order(c):
    author_token, _ = await login_account(c, "google", "a")
    a_auth = {"Authorization": f"Bearer {author_token}"}
    book = (await c.post("/api/books", json={"title": "웹훅책"}, headers=a_auth)).json()["bookId"]
    await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
    await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
    buyer_token, _ = await login_account(c, "naver", "b")
    b_auth = {"Authorization": f"Bearer {buyer_token}"}
    oid = (await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=b_auth)).json()["id"]
    await c.post(f"/api/orders/{oid}/confirm", json={"pgTxId": "tx"}, headers=b_auth)
    return oid, b_auth


async def test_webhook_cancel_reconciles_to_refunded(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        oid, b_auth = await _paid_order(c)
        assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).json()["status"] == "PAID"

        # PG가 취소 상태로 보고 → 웹훅 reconcile → 환불
        GATEWAY.status = "CANCELED"
        r = await c.post("/api/payments/webhook", json={"data": {"orderId": oid, "status": "CANCELED"}})
        assert r.status_code == 200 and r.json()["ok"] is True
        assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).json()["status"] == "REFUNDED"


async def test_webhook_body_not_trusted(app_db):
    """바디가 CANCELED라 주장해도 PG 실제 상태가 DONE이면 환불 안 함(위조 방어)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        oid, b_auth = await _paid_order(c)
        GATEWAY.status = "DONE"  # PG는 정상 결제로 보고
        await c.post("/api/payments/webhook", json={"data": {"orderId": oid, "status": "CANCELED"}})
        assert (await c.get(f"/api/orders/{oid}", headers=b_auth)).json()["status"] == "PAID"


async def test_webhook_unknown_order_still_200(app_db):
    import uuid

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/payments/webhook", json={"orderId": str(uuid.uuid4())})
        assert r.status_code == 200
        r2 = await c.post("/api/payments/webhook", json={"garbage": True})
        assert r2.status_code == 200
