"""GET /api/books/{id}/epub 다운로드 게이트 회귀 테스트.

2026-07-08 연령게이트 감사 중 발견: 이 엔드포인트는 인증·구매 확인이 전혀 없어
book_id(스토어 URL에 노출)만 알면 누구나 무료로 유료책 전체 EPUB을 받을 수 있었다.
/content 엔드포인트와 동일한 is_free/owned 기준으로 게이트했다 — 이 테스트가 회귀를 잡는다.
"""
import uuid

import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import create_book
from tests.integration.order_helpers import buy_book

_AUTHOR = SocialProfile("GOOGLE", "epub-author", "author@x.com", "작가")


@pytest.fixture
def social_profile():
    return _AUTHOR


async def _publish_priced_book(client, auth, price=5000):
    book = await create_book(client, auth, title="유료책")
    await client.post(f"/api/books/{book}/import", json={"rawText": "# 1장\n\n본문."}, headers=auth)
    await client.put(f"/api/books/{book}/price", json={"amount": price}, headers=auth)
    await client.post(f"/api/books/{book}/publish-now", headers=auth)
    return book


async def test_unauthenticated_cannot_download_paid_book_epub(client):
    """회귀가드 핵심 — 로그인 없이 book_id만으로 접근 → 403(과거엔 200+무료 epub)."""
    token, _ = await login_account(client, "google", "epub-author")
    auth = {"Authorization": f"Bearer {token}"}
    book = await _publish_priced_book(client, auth)

    r = await client.get(f"/api/books/{book}/epub")
    assert r.status_code == 403


async def test_other_account_without_purchase_cannot_download(client):
    """제3자가 로그인은 했지만 구매 안 함 → 403."""
    token, _ = await login_account(client, "google", "epub-author")
    auth = {"Authorization": f"Bearer {token}"}
    book = await _publish_priced_book(client, auth)

    other_token, _ = await login_account(client, "google", "epub-stranger")
    other_auth = {"Authorization": f"Bearer {other_token}"}
    r = await client.get(f"/api/books/{book}/epub", headers=other_auth)
    assert r.status_code == 403


async def test_buyer_can_download_purchased_book_epub(client):
    """실제 구매자는 200 + 진짜 epub 바이너리를 받는다."""
    token, _ = await login_account(client, "google", "epub-author")
    auth = {"Authorization": f"Bearer {token}"}
    book = await _publish_priced_book(client, auth)

    buyer_token, _ = await login_account(client, "google", "epub-buyer")
    buyer_auth = {"Authorization": f"Bearer {buyer_token}"}
    await buy_book(client, buyer_auth, book)

    r = await client.get(f"/api/books/{book}/epub", headers=buyer_auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/epub+zip"
    assert len(r.content) > 0


async def test_free_book_epub_downloadable_without_purchase(client):
    """무료책(가격 미설정)은 구매 없이도 다운로드 가능 — 기존 무료책 배포 취지 유지."""
    token, _ = await login_account(client, "google", "epub-author")
    auth = {"Authorization": f"Bearer {token}"}
    book = await create_book(client, auth, title="무료책")
    await client.post(f"/api/books/{book}/import", json={"rawText": "# 1장\n\n무료 본문."}, headers=auth)
    await client.post(f"/api/books/{book}/publish-now", headers=auth)

    r = await client.get(f"/api/books/{book}/epub")
    assert r.status_code == 200


async def test_download_unknown_book_404(client):
    r = await client.get(f"/api/books/{uuid.uuid4()}/epub")
    assert r.status_code == 404
