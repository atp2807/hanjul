"""GET /api/books/{id}/epub 다운로드 게이트 회귀 테스트.

2026-07-08 연령게이트 감사 중 발견: 이 엔드포인트는 인증·구매 확인이 전혀 없어
book_id(스토어 URL에 노출)만 알면 누구나 무료로 유료책 전체 EPUB을 받을 수 있었다.
/content 엔드포인트와 동일한 is_free/owned(+저자 우회) 기준으로 게이트했다.

⚠️ 계정 분리: login_account(OAuth 콜백 경유)는 conftest의 `social_profile` 픽스처 값
하나로 고정돼 있어(FakeProvider가 code 인자를 무시) 여러 번 불러도 전부 같은 계정이 된다
(2026-07-08 이 파일 초안에서 실제로 겪은 버그 — "stranger"가 몰래 author와 동일계정이라
403이어야 할 테스트가 우연히 통과함). test_manuscript_backup_e2e.py의 선례대로
token_issuer()로 서로 다른 UUID를 직접 발급해 진짜 다계정을 만든다(SQLite는 FK 강제 안 함).
"""
import uuid

from src.features.auth.presentation.dependencies import token_issuer

from tests.integration.order_helpers import buy_book


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _issue(role="AUTHOR"):
    issuer = token_issuer()
    return issuer.issue(uuid.uuid4(), role)


async def _create_book(client, auth, title="유료책"):
    r = await client.post("/api/books", json={"title": title, "kind": "BOOK"}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()["bookId"]


async def _publish_priced_book(client, auth, price=5000, title="유료책"):
    book = await _create_book(client, auth, title=title)
    r = await client.post(f"/api/books/{book}/import", json={"rawText": "# 1장\n\n본문."}, headers=auth)
    assert r.status_code == 200, r.text
    r = await client.put(f"/api/books/{book}/price", json={"amount": price}, headers=auth)
    assert r.status_code == 204, r.text
    r = await client.post(f"/api/books/{book}/publish-now", headers=auth)
    assert r.status_code == 204, r.text
    return book


async def test_unauthenticated_cannot_download_paid_book_epub(client):
    """회귀가드 핵심 — 로그인 없이 book_id만으로 접근 → 403(과거엔 200+무료 epub)."""
    author = _auth(_issue())
    book = await _publish_priced_book(client, author)

    r = await client.get(f"/api/books/{book}/epub")
    assert r.status_code == 403


async def test_other_account_without_purchase_cannot_download(client):
    """제3자(진짜 다른 계정)가 로그인은 했지만 구매 안 함 → 403."""
    author = _auth(_issue())
    book = await _publish_priced_book(client, author)

    stranger = _auth(_issue())  # author와 다른 uuid4 — 진짜 별개 계정
    r = await client.get(f"/api/books/{book}/epub", headers=stranger)
    assert r.status_code == 403


async def test_author_can_download_own_priced_unpurchased_book(client):
    """회귀가드 — 저자 본인은 자기 유료책을 구매(주문) 없이도 다운로드 가능해야 한다.
    (실사고: 이 우회 없이 배포했다가 e2e '작가 생성→출간→서점배포' 흐름이 실제로 깨짐 —
    저자가 가격을 매긴 자기 책의 EPUB을 스튜디오에서 못 받는 회귀였음.)"""
    author = _auth(_issue())
    book = await _publish_priced_book(client, author)

    r = await client.get(f"/api/books/{book}/epub", headers=author)
    assert r.status_code == 200
    assert len(r.content) > 0


async def test_buyer_can_download_purchased_book_epub(client):
    """실제 구매자(진짜 다른 계정)는 200 + 진짜 epub 바이너리를 받는다."""
    author = _auth(_issue())
    book = await _publish_priced_book(client, author)

    buyer = _auth(_issue())
    await buy_book(client, buyer, book)

    r = await client.get(f"/api/books/{book}/epub", headers=buyer)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/epub+zip"
    assert len(r.content) > 0


async def test_free_book_epub_downloadable_without_purchase(client):
    """무료책(가격 미설정)은 구매 없이도 다운로드 가능 — 기존 무료책 배포 취지 유지."""
    author = _auth(_issue())
    book = await _create_book(client, author, title="무료책")
    await client.post(f"/api/books/{book}/import", json={"rawText": "# 1장\n\n무료 본문."}, headers=author)
    await client.post(f"/api/books/{book}/publish-now", headers=author)

    r = await client.get(f"/api/books/{book}/epub")
    assert r.status_code == 200


async def test_download_unknown_book_404(client):
    r = await client.get(f"/api/books/{uuid.uuid4()}/epub")
    assert r.status_code == 404
