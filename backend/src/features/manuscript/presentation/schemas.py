"""manuscript API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class ChapterPushRequest(CamelSchema):
    chapter_key: str
    title: str
    html: str
    content_hash: str


class ManuscriptPushRequest(CamelSchema):
    title: str
    chapters: list[ChapterPushRequest] = []


class ManuscriptPushResponse(CamelSchema):
    saved_count: int
    skipped_count: int


class ChapterStateResponse(CamelSchema):
    chapter_key: str
    title: str
    html: str
    content_hash: str
    updated_at: datetime


class ManuscriptStateResponse(CamelSchema):
    sync_key: UUID
    title: str
    chapters: list[ChapterStateResponse]
