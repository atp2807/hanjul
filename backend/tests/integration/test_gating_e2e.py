"""읽기 미리보기 게이팅 E2E — 유료책은 미구매=앞3블록, 구매=전체."""
import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book, import_raw
from tests.integration.order_helpers import buy_book


def _count_blocks(content):
    return sum(len(ch["blocks"]) for ch in content["chapters"])


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "g-sub", "g@x.com", "독자")


async def test_preview_for_non_owner_full_for_owner(client_orders):
    c = client_orders
    # 5블록짜리 유료책 준비 (작가 인증으로 생성 → 변경 권한)
    token, _ = await login_account(c, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book_id = await create_book(c, auth, title="유료책")
    await import_raw(c, book_id, "1\n\n2\n\n3\n\n4\n\n5", auth)
    await c.put(f"/api/books/{book_id}/price", json={"amount": 5000}, headers=auth)
    await c.post(f"/api/books/{book_id}/submit", headers=auth)
    await c.post(f"/api/books/{book_id}/publish", headers=auth)

    # 미로그인 → 미리보기 3블록
    anon = (await c.get(f"/api/books/{book_id}/content")).json()
    assert anon["isPreview"] is True
    assert _count_blocks(anon) == 3

    # 로그인했지만 미구매 → 여전히 미리보기
    token, _me = await login_account(c, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    before = (await c.get(f"/api/books/{book_id}/content", headers=auth)).json()
    assert before["isPreview"] is True and _count_blocks(before) == 3

    # 구매 후 → 전체 (금액은 서버 도출)
    await buy_book(c, auth, book_id)

    after = (await c.get(f"/api/books/{book_id}/content", headers=auth)).json()
    assert after["isPreview"] is False
    assert _count_blocks(after) == 5


async def test_free_book_is_full_without_login(client_orders):
    c = client_orders
    book_id = await create_book(c, title="무료책")
    await import_raw(c, book_id, "1\n\n2\n\n3\n\n4")
    # 가격 미설정(무료) → 미로그인도 전체
    res = (await c.get(f"/api/books/{book_id}/content")).json()
    assert res["isPreview"] is False
    assert _count_blocks(res) == 4
