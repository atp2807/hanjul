"""notifications 도메인 — 알림 뷰 + 팔로우/알림 리포지토리 포트."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

NEW_BOOK = "NEW_BOOK"
REVISION = "REVISION"
ASSIGNED = "ASSIGNED"   # 서평단 배정 — 증정본 도착 안내


@dataclass
class NotificationView:
    id: UUID
    kind_cd: str
    book_id: UUID | None
    title: str | None
    read_yn: bool
    created_at: datetime


class FollowRepository(Protocol):
    async def follow(self, follower_id: UUID, author_id: UUID) -> None:
        """멱등 — 이미 팔로우면 무시."""
        ...

    async def unfollow(self, follower_id: UUID, author_id: UUID) -> None:
        ...

    async def is_following(self, follower_id: UUID, author_id: UUID) -> bool:
        ...

    async def follower_ids(self, author_id: UUID) -> list[UUID]:
        ...


class NotificationRepository(Protocol):
    async def create_for_recipients(
        self, recipient_ids: list[UUID], kind_cd: str, book_id: UUID | None, title: str | None
    ) -> None:
        """수신자별 알림 생성. (수신자,책,종류) 중복은 건너뜀(멱등 — 신간용)."""
        ...

    async def relight_for_recipients(
        self, recipient_ids: list[UUID], kind_cd: str, book_id: UUID | None, title: str | None
    ) -> None:
        """수신자별 알림 재점등 — 기존 (수신자,책,종류)면 안읽음으로 되살림, 없으면 생성(개정판용)."""
        ...

    async def list_for(self, recipient_id: UUID) -> list[NotificationView]:
        ...

    async def mark_read(self, recipient_id: UUID, notification_id: UUID) -> bool:
        """본인 알림만 읽음 처리. 대상 없으면 False."""
        ...

    async def mark_all_read(self, recipient_id: UUID) -> None:
        ...
