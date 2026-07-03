"""엔드포인트 HTTP 에러 매핑 검증 — 404/409/422/400 상태코드.

서비스 로직(전이규칙·구매불가 등)은 단위 테스트로 커버됨. 여기선 그게 올바른
HTTP 상태로 변환되는지(except→HTTPException)를 실 흐름으로 확정한다.
"""
import uuid

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

PROFILE = SocialProfile("GOOGLE", "err-x", "e@x.com", "유저")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", PROFILE)}, token_issuer()
        )

    def _order(session: AsyncSession = Depends(get_session)):
        return OrderService(SqlOrderRepository(session), FakeGateway(ok=True), SqlBookPricing(session))

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    app.dependency_overrides[get_order_service] = _order
    yield
    app.dependency_overrides.clear()


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_catalog_http_errors(app_db):
    rnd = uuid.uuid4()
    async with _client() as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        # 없는 책 → 404 (인증+소유 게이트 뒤)
        assert (await c.put(f"/api/books/{rnd}/price", json={"amount": 1000}, headers=auth)).status_code == 404
        assert (await c.post(f"/api/books/{rnd}/submit", headers=auth)).status_code == 404
        assert (await c.get(f"/api/store/books/{rnd}")).status_code == 404  # 미출판 비공개

        book = (await c.post("/api/books", json={"title": "x"}, headers=auth)).json()["bookId"]
        # DRAFT에서 바로 출판 → 409 (전이 위반)
        assert (await c.post(f"/api/books/{book}/publish", headers=auth)).status_code == 409
        # 음수 가격 → 422
        assert (await c.put(f"/api/books/{book}/price", json={"amount": -5}, headers=auth)).status_code == 422
        # 가격 없이 심사→출판 → 422 (PriceRequired)
        await c.post(f"/api/books/{book}/submit", headers=auth)
        assert (await c.post(f"/api/books/{book}/publish", headers=auth)).status_code == 422


async def test_billing_http_errors(app_db):
    async with _client() as c:
        token, _ = await login_account(c, "google", "a")
        auth = {"Authorization": f"Bearer {token}"}
        rnd = uuid.uuid4()

        # 미출판 책 구매 → 404 (NotPurchasable)
        book = (await c.post("/api/books", json={"title": "x"}, headers=auth)).json()["bookId"]
        assert (await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=auth)).status_code == 404
        # 없는 주문 confirm / 조회 → 404
        assert (await c.post(f"/api/orders/{rnd}/confirm", json={"pgTxId": "x"}, headers=auth)).status_code == 404
        assert (await c.get(f"/api/orders/{rnd}", headers=auth)).status_code == 404

        # 출판 후 구매 → 이중 confirm 409, 재구매 409
        await c.put(f"/api/books/{book}/price", json={"amount": 1000}, headers=auth)
        await c.post(f"/api/books/{book}/submit", headers=auth)
        await c.post(f"/api/books/{book}/publish", headers=auth)
        oid = (await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=auth)).json()["id"]
        await c.post(f"/api/orders/{oid}/confirm", json={"pgTxId": "x"}, headers=auth)
        assert (await c.post(f"/api/orders/{oid}/confirm", json={"pgTxId": "x"}, headers=auth)).status_code == 409
        assert (await c.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=auth)).status_code == 409


async def test_cover_missing_book_404(app_db):
    async with _client() as c:
        # 무인증이면 404보다 401이 먼저 (표지 생성은 소유 작가만)
        assert (await c.post(f"/api/books/{uuid.uuid4()}/cover", json={"prompt": "x"})).status_code == 401
        token, _ = await login_account(c, "google", "x")
        r = await c.post(
            f"/api/books/{uuid.uuid4()}/cover", json={"prompt": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404


async def test_auth_unknown_provider_callback_400(app_db):
    async with _client() as c:
        assert (await c.get("/api/auth/unknownprov/callback?code=x")).status_code == 400


async def test_me_account_not_found_404(app_db):
    # 존재하지 않는 계정 id로 서명된 토큰 → /me 404
    token = token_issuer().issue(uuid.uuid4(), "READER")
    async with _client() as c:
        assert (await c.get("/api/me", headers={"Authorization": f"Bearer {token}"})).status_code == 404
