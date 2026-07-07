"""인앱 알림함 E2E — 작가 팔로우 → 신간 출판 → 팔로워만 알림(멱등)."""
import uuid

import pytest
from fastapi import Depends
from main import app
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_session
from src.features.auth.application.auth_service import AuthService
from src.features.auth.domain.models import SocialProfile
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer

from tests.fixtures.fake_account_repo import FakeProvider
from tests.integration.auth_helpers import login_account
from tests.integration.book_helpers import publish_priced_book
from tests.integration.order_helpers import buy_book

AUTHOR = SocialProfile("GOOGLE", "n-author", "author@x.com", "작가한")
FOLLOWER = SocialProfile("NAVER", "n-follower", "f@x.com", "팔로워")
OTHER = SocialProfile("KAKAO", "n-other", "o@x.com", "남")


@pytest.fixture
def app_db(sessionmaker):
    """3-provider(작가·팔로워·타인) 동시 로그인이 필요 — conftest의 단일 social_profile app_db로 못 대체."""
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {
                "GOOGLE": FakeProvider("GOOGLE", AUTHOR),
                "NAVER": FakeProvider("NAVER", FOLLOWER),
                "KAKAO": FakeProvider("KAKAO", OTHER),
            },
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_follow_then_new_book_notifies_only_followers(client_orders):
    c = client_orders
    author_token, author = await login_account(c, "google", "a")
    follower_token, _ = await login_account(c, "naver", "f")
    other_token, _ = await login_account(c, "kakao", "o")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    follower_auth = {"Authorization": f"Bearer {follower_token}"}
    other_auth = {"Authorization": f"Bearer {other_token}"}
    author_id = author["id"]

    # 팔로워만 작가 구독
    assert (await c.post(f"/api/authors/{author_id}/follow", headers=follower_auth)).status_code == 204
    assert (await c.get(f"/api/authors/{author_id}/follow", headers=follower_auth)).json()["following"] is True
    assert (await c.get(f"/api/authors/{author_id}/follow", headers=other_auth)).json()["following"] is False

    book = await publish_priced_book(c, author_auth, title="신간", price=5000, raw_text="1\n\n2")

    # 팔로워: 신간 알림 1건
    inbox = (await c.get("/api/me/notifications", headers=follower_auth)).json()
    assert inbox["unreadCount"] == 1
    assert inbox["items"][0]["kind"] == "NEW_BOOK"
    assert inbox["items"][0]["bookId"] == book
    assert inbox["items"][0]["title"] == "신간"
    assert inbox["items"][0]["isRead"] is False

    # 비팔로워·작가 본인: 알림 없음
    assert (await c.get("/api/me/notifications", headers=other_auth)).json()["unreadCount"] == 0
    assert (await c.get("/api/me/notifications", headers=author_auth)).json()["unreadCount"] == 0

    # 읽음 처리
    nid = inbox["items"][0]["id"]
    assert (await c.post(f"/api/me/notifications/{nid}/read", headers=follower_auth)).status_code == 204
    assert (await c.get("/api/me/notifications", headers=follower_auth)).json()["unreadCount"] == 0

    # 재발행(비공개→재출판) 해도 알림 중복 안 됨(멱등)
    await c.post(f"/api/books/{book}/unpublish", headers=author_auth)
    await c.post(f"/api/books/{book}/publish-now", headers=author_auth)
    again = (await c.get("/api/me/notifications", headers=follower_auth)).json()
    assert len(again["items"]) == 1 and again["unreadCount"] == 0


async def test_unfollow_stops_notifications(client_orders):
    c = client_orders
    author_token, author = await login_account(c, "google", "a")
    follower_token, _ = await login_account(c, "naver", "f")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    follower_auth = {"Authorization": f"Bearer {follower_token}"}
    author_id = author["id"]

    await c.post(f"/api/authors/{author_id}/follow", headers=follower_auth)
    assert (await c.delete(f"/api/authors/{author_id}/follow", headers=follower_auth)).status_code == 204

    await publish_priced_book(c, author_auth, title="언팔후신간", price=5000, raw_text="1\n\n2")
    assert (await c.get("/api/me/notifications", headers=follower_auth)).json()["unreadCount"] == 0


async def test_full_publish_path_also_notifies(client_orders):
    """publish-now 뿐 아니라 심사→publish 경로도 알림 발생."""
    c = client_orders
    author_token, author = await login_account(c, "google", "a")
    follower_token, _ = await login_account(c, "naver", "f")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    follower_auth = {"Authorization": f"Bearer {follower_token}"}

    await c.post(f"/api/authors/{author['id']}/follow", headers=follower_auth)
    book = (await c.post("/api/books", json={"title": "심사책"}, headers=author_auth)).json()["bookId"]
    await c.put(f"/api/books/{book}/price", json={"amount": 3000}, headers=author_auth)
    await c.post(f"/api/books/{book}/submit", headers=author_auth)
    assert (await c.post(f"/api/books/{book}/publish", headers=author_auth)).status_code == 204

    assert (await c.get("/api/me/notifications", headers=follower_auth)).json()["unreadCount"] == 1


async def test_revision_notifies_buyers_and_relights(client_orders):
    """이미 출판된 책을 재발행(개정판) → 구매자에게 REVISION 알림. 재개정 시 재점등."""
    c = client_orders
    author_token, _ = await login_account(c, "google", "a")
    buyer_token, _ = await login_account(c, "naver", "b")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    buyer_auth = {"Authorization": f"Bearer {buyer_token}"}

    book = await publish_priced_book(c, author_auth, title="개정대상", price=5000, raw_text="1\n\n2")  # 첫 출판(PUBLISHED)

    # 구매자 구매 + 확정
    await buy_book(c, buyer_auth, book)
    # 구매 자체로는 알림 없음
    assert (await c.get("/api/me/notifications", headers=buyer_auth)).json()["unreadCount"] == 0

    # 작가가 재발행(개정판) → 구매자 REVISION 알림
    await c.post(f"/api/books/{book}/publish-now", headers=author_auth)
    inbox = (await c.get("/api/me/notifications", headers=buyer_auth)).json()
    assert inbox["unreadCount"] == 1
    assert inbox["items"][0]["kind"] == "REVISION"
    assert inbox["items"][0]["bookId"] == book

    # 읽음 → 0
    nid = inbox["items"][0]["id"]
    await c.post(f"/api/me/notifications/{nid}/read", headers=buyer_auth)
    assert (await c.get("/api/me/notifications", headers=buyer_auth)).json()["unreadCount"] == 0

    # 다시 개정 → 같은 알림이 재점등(행 1개 유지, 다시 안읽음)
    await c.post(f"/api/books/{book}/publish-now", headers=author_auth)
    again = (await c.get("/api/me/notifications", headers=buyer_auth)).json()
    revisions = [n for n in again["items"] if n["kind"] == "REVISION"]
    assert len(revisions) == 1 and again["unreadCount"] == 1


async def test_scheduled_publish_notifies_followers(client, sessionmaker):
    """예약발행(스케줄러 자동 게시) 경로도 팔로워에게 신간 알림."""
    from datetime import UTC, datetime, timedelta

    from main import publish_due_and_notify

    c = client
    author_token, author = await login_account(c, "google", "a")
    follower_token, _ = await login_account(c, "naver", "f")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    follower_auth = {"Authorization": f"Bearer {follower_token}"}

    await c.post(f"/api/authors/{author['id']}/follow", headers=follower_auth)

    # 과거 시각으로 예약 (아직 DRAFT, 게시 안 됨)
    book = (await c.post("/api/books", json={"title": "예약신간"}, headers=author_auth)).json()["bookId"]
    await c.put(f"/api/books/{book}/price", json={"amount": 4000}, headers=author_auth)
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    await c.post(f"/api/books/{book}/schedule", json={"publishAt": past}, headers=author_auth)

    # 아직 알림 없음
    assert (await c.get("/api/me/notifications", headers=follower_auth)).json()["unreadCount"] == 0

    # 스케줄러 본체 실행 → 게시 + 신간 알림
    async with sessionmaker() as s:
        n = await publish_due_and_notify(s, datetime.now(UTC))
    assert n == 1

    inbox = (await c.get("/api/me/notifications", headers=follower_auth)).json()
    assert inbox["unreadCount"] == 1
    assert inbox["items"][0]["kind"] == "NEW_BOOK"
    assert inbox["items"][0]["bookId"] == book


async def test_follow_gates(client):
    c = client
    author_token, author = await login_account(c, "google", "a")
    author_auth = {"Authorization": f"Bearer {author_token}"}
    author_id = author["id"]

    # 미인증 → 401
    assert (await c.post(f"/api/authors/{author_id}/follow")).status_code == 401
    assert (await c.get("/api/me/notifications")).status_code == 401
    # 없는 작가 → 404
    assert (await c.post(f"/api/authors/{uuid.uuid4()}/follow", headers=author_auth)).status_code == 404
    # 자기 자신 → 400
    assert (await c.post(f"/api/authors/{author_id}/follow", headers=author_auth)).status_code == 400
    # 없는 알림 읽음 → 404
    assert (
        await c.post(f"/api/me/notifications/{uuid.uuid4()}/read", headers=author_auth)
    ).status_code == 404
