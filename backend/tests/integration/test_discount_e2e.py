"""기간 할인 E2E — 주문 금액이 서버에서 할인 반영(클라 못 건드림) + 만료 처리."""
from datetime import UTC, datetime, timedelta

import pytest
from src.config.settings import settings
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book

settings.PAYMENT_DEMO = True


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "disc", "d@x.com", "구매자")


async def _publish(c, auth, price):
    book = await create_book(c, auth, title="할인책")
    await c.put(f"/api/books/{book}/price", json={"amount": price}, headers=auth)
    await c.post(f"/api/books/{book}/publish-now", headers=auth)
    return book


async def test_active_discount_applies_to_order(client):
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await _publish(client, auth, 10000)

    until = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert (await client.put(f"/api/books/{book}/discount", json={"amount": 6000, "until": until}, headers=auth)).status_code == 204

    # 스토어 상세에 할인 노출
    detail = (await client.get(f"/api/store/books/{book}")).json()
    assert detail["priceAmt"] == 10000 and detail["discountAmt"] == 6000

    # 주문 금액 = 할인가 (서버 도출, 본문 금액 무시)
    order = (await client.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=auth)).json()
    assert order["amountAmt"] == 6000


async def test_expired_discount_uses_original(client):
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await _publish(client, auth, 10000)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    await client.put(f"/api/books/{book}/discount", json={"amount": 6000, "until": past}, headers=auth)

    order = (await client.post("/api/orders", json={"bookId": book, "withdrawalConsent": True}, headers=auth)).json()
    assert order["amountAmt"] == 10000  # 만료 → 정가
