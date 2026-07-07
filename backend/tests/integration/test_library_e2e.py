"""내 서재 E2E — 로그인 → 구매 → /me/library 에 등장."""
import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book
from tests.integration.order_helpers import buy_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "lib-sub", "lib@x.com", "독자")


async def test_purchased_book_appears_in_library(client_orders):
    c = client_orders
    token, _me = await login_account(c, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}

    # 미로그인 → 401
    assert (await c.get("/api/me/library")).status_code == 401
    # 처음엔 빈 서재
    assert (await c.get("/api/me/library", headers=auth)).json() == []

    # 책 생성 → 출판(가격) → 구매 → 결제확인
    book_id = await create_book(c, auth, title="산 책")
    await c.put(f"/api/books/{book_id}/price", json={"amount": 8000}, headers=auth)
    await c.post(f"/api/books/{book_id}/submit", headers=auth)
    await c.post(f"/api/books/{book_id}/publish", headers=auth)
    await buy_book(c, auth, book_id)

    # 서재에 등장
    lib = (await c.get("/api/me/library", headers=auth)).json()
    assert len(lib) == 1
    assert lib[0]["bookId"] == book_id
    assert lib[0]["title"] == "산 책"
