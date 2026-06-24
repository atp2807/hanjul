"""catalog API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class AssignAuthorRequest(_Camel):
    author_id: UUID


class SetPriceRequest(_Camel):
    amount: int  # 원 단위 정수


class SetIsbnRequest(_Camel):
    isbn: str


class UpdateMetaRequest(_Camel):
    subtitle: str | None = None
    description: str | None = None
    category: str | None = None


class SchedulePublishRequest(_Camel):
    publish_at: datetime


class BookSummaryResponse(_Camel):
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


class SetDiscountRequest(_Camel):
    amount: int          # 할인가(원)
    until: datetime      # 할인 종료시각


class StoreListResponse(_Camel):
    items: list[BookSummaryResponse]
    count: int


class AuthorProfileResponse(_Camel):
    id: UUID
    display_name: str | None
    bio: str | None
    books: list[BookSummaryResponse]
