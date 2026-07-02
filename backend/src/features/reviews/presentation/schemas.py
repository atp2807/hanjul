"""reviews API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class AddReviewRequest(CamelSchema):
    rating: int           # 1~5
    body: str | None = None


class ReviewItem(CamelSchema):
    id: UUID
    rating: int
    body: str | None
    author: str | None
    created_at: datetime
    updated_at: datetime | None = None
    source: str = "PURCHASE"


class ReviewListResponse(CamelSchema):
    average: float
    count: int
    items: list[ReviewItem]
