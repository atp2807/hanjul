"""notifications API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class NotificationItem(CamelSchema):
    id: UUID
    kind_cd: str
    book_id: UUID | None
    title: str | None
    read_yn: bool
    created_at: datetime


class NotificationListResponse(CamelSchema):
    items: list[NotificationItem]
    unread_count: int


class FollowStatusResponse(CamelSchema):
    following: bool
