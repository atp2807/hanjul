"""리뷰·평점 E2E — 작성(로그인)/조회/검증/업서트."""
import uuid as _uuid

import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "rv", "r@x.com", "독자김")


async def test_review_gates(client):
    """작성 게이트: 미로그인 401 / 없는 책 404 / 미구매 403 (구매자만 리뷰)."""
    token, _ = await login_account(client, "google", "x")
    auth = {"Authorization": f"Bearer {token}"}
    book = await create_book(client, auth, title="리뷰책")

    assert (await client.post(f"/api/books/{book}/reviews", json={"rating": 5})).status_code == 401
    assert (await client.post(f"/api/books/{_uuid.uuid4()}/reviews", json={"rating": 5}, headers=auth)).status_code == 404
    # 작가 본인도 구매 안 했으면 리뷰 불가(자기책 셀프리뷰 방지)
    assert (await client.post(f"/api/books/{book}/reviews", json={"rating": 5}, headers=auth)).status_code == 403
