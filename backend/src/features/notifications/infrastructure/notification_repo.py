"""FollowRepository / NotificationRepository 의 SQLAlchemy 구현."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.notifications.domain.models import NotificationView
from src.infrastructure.db.models.notification import Follow, Notification


class SqlFollowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _find(self, follower_id: UUID, author_id: UUID):
        return (
            await self.session.execute(
                select(Follow).where(Follow.follower_id == follower_id, Follow.author_id == author_id)
            )
        ).scalar_one_or_none()

    async def follow(self, follower_id: UUID, author_id: UUID) -> None:
        if await self._find(follower_id, author_id):
            return
        self.session.add(Follow(follower_id=follower_id, author_id=author_id))
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()  # 동시 삽입 경쟁 → 멱등

    async def unfollow(self, follower_id: UUID, author_id: UUID) -> None:
        row = await self._find(follower_id, author_id)
        if row:
            await self.session.delete(row)
            await self.session.commit()

    async def is_following(self, follower_id: UUID, author_id: UUID) -> bool:
        return await self._find(follower_id, author_id) is not None

    async def follower_ids(self, author_id: UUID) -> list[UUID]:
        rows = (
            await self.session.execute(select(Follow.follower_id).where(Follow.author_id == author_id))
        ).scalars().all()
        return list(rows)


class SqlNotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_for_recipients(
        self, recipient_ids: list[UUID], kind_cd: str, book_id: UUID | None, title: str | None
    ) -> None:
        if not recipient_ids:
            return
        # 이미 같은 (수신자,책,종류) 알림 있는 수신자는 제외 (재발행 멱등)
        existing = set(
            (
                await self.session.execute(
                    select(Notification.recipient_id).where(
                        Notification.book_id == book_id,
                        Notification.kind_cd == kind_cd,
                        Notification.recipient_id.in_(recipient_ids),
                    )
                )
            ).scalars().all()
        )
        fresh = [r for r in recipient_ids if r not in existing]
        if not fresh:
            return
        self.session.add_all(
            [
                Notification(recipient_id=r, kind_cd=kind_cd, book_id=book_id, title=title)
                for r in fresh
            ]
        )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()  # 유니크 경쟁 → 멱등

    async def relight_for_recipients(
        self, recipient_ids: list[UUID], kind_cd: str, book_id: UUID | None, title: str | None
    ) -> None:
        if not recipient_ids:
            return
        existing = {
            n.recipient_id: n
            for n in (
                await self.session.execute(
                    select(Notification).where(
                        Notification.book_id == book_id,
                        Notification.kind_cd == kind_cd,
                        Notification.recipient_id.in_(recipient_ids),
                    )
                )
            ).scalars().all()
        }
        now = datetime.now(UTC)
        for r in recipient_ids:
            cur = existing.get(r)
            if cur is not None:
                cur.read_yn = False  # 다시 안읽음으로 되살림(개정판 재알림)
                cur.title = title
                cur.created_at = now
            else:
                self.session.add(
                    Notification(recipient_id=r, kind_cd=kind_cd, book_id=book_id, title=title)
                )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()  # 유니크 경쟁 → 멱등

    async def list_for(self, recipient_id: UUID) -> list[NotificationView]:
        rows = (
            await self.session.execute(
                select(Notification)
                .where(Notification.recipient_id == recipient_id)
                .order_by(Notification.created_at.desc())
            )
        ).scalars().all()
        return [
            NotificationView(
                id=n.id,
                kind_cd=n.kind_cd,
                book_id=n.book_id,
                title=n.title,
                read_yn=n.read_yn,
                created_at=n.created_at,
            )
            for n in rows
        ]

    async def mark_read(self, recipient_id: UUID, notification_id: UUID) -> bool:
        n = await self.session.get(Notification, notification_id)
        if n is None or n.recipient_id != recipient_id:
            return False
        n.read_yn = True
        await self.session.commit()
        return True

    async def mark_all_read(self, recipient_id: UUID) -> None:
        # 메모리 적재 없이 일괄 UPDATE (안읽음만)
        await self.session.execute(
            update(Notification)
            .where(Notification.recipient_id == recipient_id, Notification.read_yn.is_(False))
            .values(read_yn=True)
        )
        await self.session.commit()
