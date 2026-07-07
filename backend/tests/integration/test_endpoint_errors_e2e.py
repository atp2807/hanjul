"""엔드포인트 HTTP 에러 매핑 검증 — 404/409/422/400 상태코드.

서비스 로직(전이규칙·구매불가 등)은 단위 테스트로 커버됨. 여기선 그게 올바른
HTTP 상태로 변환되는지(except→HTTPException)를 실 흐름으로 확정한다.
"""
import uuid

import pytest
from src.features.auth.domain.models import SocialProfile
from src.features.auth.presentation.dependencies import token_issuer

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "err-x", "e@x.com", "유저")


async def test_catalog_http_errors(client_orders):
    c = client_orders
    rnd = uuid.uuid4()
    token, _ = await login_account(c, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    # 없는 책 → 404 (인증+소유 게이트 뒤)
    assert (await c.put(f"/api/books/{rnd}/price", json={"amount": 1000}, headers=auth)).status_code == 404
    assert (await c.post(f"/api/books/{rnd}/submit", headers=auth)).status_code == 404
    assert (await c.get(f"/api/store/books/{rnd}")).status_code == 404  # 미출판 비공개

    book = await create_book(c, auth, title="x")
    # DRAFT에서 바로 출판 → 409 (전이 위반)
    assert (await c.post(f"/api/books/{book}/publish", headers=auth)).status_code == 409
    # 음수 가격 → 422
    assert (await c.put(f"/api/books/{book}/price", json={"amount": -5}, headers=auth)).status_code == 422
    # 가격 없이 심사→출판 → 422 (PriceRequired)
    await c.post(f"/api/books/{book}/submit", headers=auth)
    assert (await c.post(f"/api/books/{book}/publish", headers=auth)).status_code == 422


async def test_billing_http_errors(client_orders):
    c = client_orders
    token, _ = await login_account(c, "google", "a")
    auth = {"Authorization": f"Bearer {token}"}
    rnd = uuid.uuid4()

    # 미출판 책 구매 → 404 (NotPurchasable)
    book = await create_book(c, auth, title="x")
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


async def test_cover_missing_book_404(client_orders):
    c = client_orders
    # 무인증이면 404보다 401이 먼저 (표지 생성은 소유 작가만)
    assert (await c.post(f"/api/books/{uuid.uuid4()}/cover", json={"prompt": "x"})).status_code == 401
    token, _ = await login_account(c, "google", "x")
    r = await c.post(
        f"/api/books/{uuid.uuid4()}/cover", json={"prompt": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_auth_unknown_provider_callback_400(client_orders):
    assert (await client_orders.get("/api/auth/unknownprov/callback?code=x")).status_code == 400


async def test_me_account_not_found_404(client_orders):
    # 존재하지 않는 계정 id로 서명된 토큰 → /me 404
    token = token_issuer().issue(uuid.uuid4(), "READER")
    assert (await client_orders.get("/api/me", headers={"Authorization": f"Bearer {token}"})).status_code == 404
