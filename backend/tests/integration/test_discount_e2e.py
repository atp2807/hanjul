"""기간 할인 E2E — 주문 금액이 서버에서 할인 반영(클라 못 건드림) + 만료 처리."""
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False
settings.PAYMENT_DEMO = True

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "disc", "d@x.com", "구매자")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", PROFILE)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def _publish(c, auth, price):
    book = (await c.post("/api/books", json={"title": "할인책"}, headers=auth)).json()["bookId"]
    await c.put(f"/api/books/{book}/price", json={"amount": price})
    await c.post(f"/api/books/{book}/publish-now")
    return book


async def test_active_discount_applies_to_order(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = await _publish(c, auth, 10000)

        until = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        assert (await c.put(f"/api/books/{book}/discount", json={"amount": 6000, "until": until})).status_code == 204

        # 스토어 상세에 할인 노출
        detail = (await c.get(f"/api/store/books/{book}")).json()
        assert detail["priceAmt"] == 10000 and detail["discountAmt"] == 6000

        # 주문 금액 = 할인가 (서버 도출, 본문 금액 무시)
        order = (await c.post("/api/orders", json={"bookId": book}, headers=auth)).json()
        assert order["amountAmt"] == 6000


async def test_expired_discount_uses_original(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = await _publish(c, auth, 10000)
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        await c.put(f"/api/books/{book}/discount", json={"amount": 6000, "until": past})

        order = (await c.post("/api/orders", json={"bookId": book}, headers=auth)).json()
        assert order["amountAmt"] == 10000  # 만료 → 정가
