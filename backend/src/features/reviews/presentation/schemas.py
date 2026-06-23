"""reviews API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class AddReviewRequest(_Camel):
    rating: int           # 1~5
    body: str | None = None


class ReviewItem(_Camel):
    id: UUID
    rating: int
    body: str | None
    author: str | None
    created_at: datetime


class ReviewListResponse(_Camel):
    average: float
    count: int
    items: list[ReviewItem]
