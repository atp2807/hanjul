"""인메모리 Follow/Notification 리포지토리 — 서비스 단위 테스트용."""
import uuid
from uuid import UUID

from src.features.notifications.domain.models import NotificationView


class FakeFollowRepository:
    def __init__(self) -> None:
        self.pairs: set[tuple[UUID, UUID]] = set()  # (follower, author)

    async def follow(self, follower_id: UUID, author_id: UUID) -> None:
        self.pairs.add((follower_id, author_id))

    async def unfollow(self, follower_id: UUID, author_id: UUID) -> None:
        self.pairs.discard((follower_id, author_id))

    async def is_following(self, follower_id: UUID, author_id: UUID) -> bool:
        return (follower_id, author_id) in self.pairs

    async def follower_ids(self, author_id: UUID) -> list[UUID]:
        return [f for (f, a) in self.pairs if a == author_id]


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.rows: list[NotificationView] = []

    async def create_for_recipients(self, recipient_ids, kind_cd, book_id, title) -> None:
        existing = {(n.recipient_id, n.book_id, n.kind_cd) for n in self.rows}
        for r in recipient_ids:
            if (r, book_id, kind_cd) in existing:
                continue
            from datetime import datetime, timezone

            self.rows.append(
                NotificationView(
                    id=uuid.uuid4(),
                    kind_cd=kind_cd,
                    book_id=book_id,
                    title=title,
                    read_yn=False,
                    created_at=datetime.now(timezone.utc),
                )
            )
            # recipient_id 를 뷰에 보관 (테스트 편의)
            self.rows[-1].recipient_id = r

    async def relight_for_recipients(self, recipient_ids, kind_cd, book_id, title) -> None:
        from datetime import datetime, timezone

        for r in recipient_ids:
            cur = next(
                (n for n in self.rows if getattr(n, "recipient_id", None) == r
                 and n.book_id == book_id and n.kind_cd == kind_cd),
                None,
            )
            if cur is not None:
                cur.read_yn = False
                cur.title = title
                cur.created_at = datetime.now(timezone.utc)
            else:
                self.rows.append(
                    NotificationView(
                        id=uuid.uuid4(), kind_cd=kind_cd, book_id=book_id, title=title,
                        read_yn=False, created_at=datetime.now(timezone.utc),
                    )
                )
                self.rows[-1].recipient_id = r

    async def list_for(self, recipient_id: UUID):
        return [n for n in self.rows if getattr(n, "recipient_id", None) == recipient_id]

    async def mark_read(self, recipient_id: UUID, notification_id: UUID) -> bool:
        for n in self.rows:
            if n.id == notification_id and getattr(n, "recipient_id", None) == recipient_id:
                n.read_yn = True
                return True
        return False

    async def mark_all_read(self, recipient_id: UUID) -> None:
        for n in self.rows:
            if getattr(n, "recipient_id", None) == recipient_id:
                n.read_yn = True
