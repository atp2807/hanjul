"""catalog API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class SetPriceRequest(CamelSchema):
    amount: int  # 원 단위 정수


class SetIsbnRequest(CamelSchema):
    isbn: str


class UpdateMetaRequest(CamelSchema):
    subtitle: str | None = None
    description: str | None = None
    category: str | None = None


class SchedulePublishRequest(CamelSchema):
    publish_at: datetime


class BookSummaryResponse(CamelSchema):
    id: UUID
    title: str
    subtitle: str | None
    author_id: UUID | None
    kind: str
    language: str
    status: str
    price_amt: int | None
    cover_url: str | None
    published_at: datetime | None
    isbn: str | None = None
    description: str | None = None
    category: str | None = None
    discount_amt: int | None = None
    discount_until: datetime | None = None
    content_rating: str = "ALL"


class SetDiscountRequest(CamelSchema):
    amount: int          # 할인가(원)
    until: datetime      # 할인 종료시각


class StoreListResponse(CamelSchema):
    items: list[BookSummaryResponse]
    count: int


class AuthorProfileResponse(CamelSchema):
    id: UUID
    display_name: str | None
    bio: str | None
    books: list[BookSummaryResponse]
