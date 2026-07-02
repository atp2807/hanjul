"""서평단 증정본 — 0원 권한으로 리뷰 가능 + 리뷰 source=REVIEW_COPY + 매출 제외."""
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

AUTHOR = SocialProfile("GOOGLE", "rc-author", "a@x.com", "작가")
REVIEWER = SocialProfile("NAVER", "rc-reviewer", "r@x.com", "서평단원")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR), "NAVER": FakeProvider("NAVER", REVIEWER)},
            token_issuer(),
        )

    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


async def test_review_copy_grants_review_and_marks_source(app_db, sessionmaker):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        reviewer_token, reviewer = await login_account(c, "naver", "r")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        rv_auth = {"Authorization": f"Bearer {reviewer_token}"}

        book = (await c.post("/api/books", json={"title": "서평책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 10000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)

        import uuid as _u
        # 안 산 사람은 리뷰 불가 (403)
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5}, headers=rv_auth)).status_code == 403

        # 서평단 증정본 지급 (캠페인 엔드포인트는 아직 없어 repo로 직접)
        async with sessionmaker() as s:
            await SqlOrderRepository(s).grant_review_copy(_u.UUID(book), _u.UUID(reviewer["id"]))

        # 증정본 권한으로 리뷰 작성 → source=REVIEW_COPY
        assert (await c.post(f"/api/books/{book}/reviews", json={"rating": 5, "body": "사전에 읽었어요"}, headers=rv_auth)).status_code == 201
        item = (await c.get(f"/api/books/{book}/reviews")).json()["items"][0]
        assert item["source"] == "REVIEW_COPY"

        # 증정본은 작가 매출에서 제외 (0원·REVIEW 채널)
        sales = (await c.get("/api/me/sales", headers=a_auth)).json()
        assert sales["totalOrders"] == 0 and sales["totalRevenue"] == 0


async def test_normal_purchase_review_is_purchase_source(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        author_token, _ = await login_account(c, "google", "a")
        buyer_token, _ = await login_account(c, "naver", "r")
        a_auth = {"Authorization": f"Bearer {author_token}"}
        b_auth = {"Authorization": f"Bearer {buyer_token}"}

        book = (await c.post("/api/books", json={"title": "구매책"}, headers=a_auth)).json()["bookId"]
        await c.put(f"/api/books/{book}/price", json={"amount": 5000}, headers=a_auth)
        await c.post(f"/api/books/{book}/publish-now", headers=a_auth)
        oid = (await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=b_auth)).json()["id"]
        await c.post(f"/api/orders/{oid}/confirm", json={"pgTxId": "tx"}, headers=b_auth)

        await c.post(f"/api/books/{book}/reviews", json={"rating": 4, "body": "샀어요"}, headers=b_auth)
        item = (await c.get(f"/api/books/{book}/reviews")).json()["items"][0]
        assert item["source"] == "PURCHASE"
