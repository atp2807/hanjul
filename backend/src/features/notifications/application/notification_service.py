"""notifications 서비스 — 팔로우 + 신간 알림 팬아웃 + 알림함 조회/읽음."""
from uuid import UUID

from src.features.notifications.domain.models import (
    NEW_BOOK,
    REVISION,
    FollowRepository,
    NotificationRepository,
    NotificationView,
)


class NotificationService:
    def __init__(self, follows: FollowRepository, notifs: NotificationRepository):
        self.follows = follows
        self.notifs = notifs

    # ── 팔로우 ────────────────────────────────────────
    async def follow(self, follower_id: UUID, author_id: UUID) -> None:
        if follower_id == author_id:
            raise ValueError("자기 자신은 팔로우할 수 없어요")
        await self.follows.follow(follower_id, author_id)

    async def unfollow(self, follower_id: UUID, author_id: UUID) -> None:
        await self.follows.unfollow(follower_id, author_id)

    async def is_following(self, follower_id: UUID, author_id: UUID) -> bool:
        return await self.follows.is_following(follower_id, author_id)

    # ── 신간 알림 팬아웃 (출판 성공 후 호출) ─────────────
    async def notify_new_book(self, book_id: UUID, author_id: UUID | None, title: str | None) -> int:
        """작가의 팔로워 전원에게 신간 알림. 작가 본인·중복은 제외. 보낸 수 반환."""
        if author_id is None:
            return 0
        recipients = [f for f in await self.follows.follower_ids(author_id) if f != author_id]
        if not recipients:
            return 0
        await self.notifs.create_for_recipients(recipients, NEW_BOOK, book_id, title)
        return len(recipients)

    async def notify_revision(self, book_id: UUID, title: str | None, buyer_ids: list[UUID]) -> int:
        """개정판 재발행 — 구매자에게 알림 재점등(매 개정마다 다시 안읽음). 보낸 수 반환."""
        if not buyer_ids:
            return 0
        await self.notifs.relight_for_recipients(buyer_ids, REVISION, book_id, title)
        return len(buyer_ids)

    # ── 알림함 ────────────────────────────────────────
    async def inbox(self, recipient_id: UUID) -> tuple[list[NotificationView], int]:
        # 전체 목록을 이미 가져오므로 안읽음 수는 거기서 도출(쿼리 1번)
        items = await self.notifs.list_for(recipient_id)
        unread = sum(1 for n in items if not n.read_yn)
        return items, unread

    async def mark_read(self, recipient_id: UUID, notification_id: UUID) -> bool:
        return await self.notifs.mark_read(recipient_id, notification_id)

    async def mark_all_read(self, recipient_id: UUID) -> None:
        await self.notifs.mark_all_read(recipient_id)
