"""notifications API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class NotificationItem(_Camel):
    id: UUID
    kind_cd: str
    book_id: UUID | None
    title: str | None
    read_yn: bool
    created_at: datetime


class NotificationListResponse(_Camel):
    items: list[NotificationItem]
    unread_count: int


class FollowStatusResponse(_Camel):
    following: bool
