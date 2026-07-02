"""notifications API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class NotificationItem(CamelSchema):
    id: UUID
    kind: str
    book_id: UUID | None
    title: str | None
    is_read: bool
    created_at: datetime


class NotificationListResponse(CamelSchema):
    items: list[NotificationItem]
    unread_count: int


class FollowStatusResponse(CamelSchema):
    following: bool
