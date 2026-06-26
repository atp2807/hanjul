"""campaigns API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class CreateCampaignRequest(_Camel):
    book_id: UUID
    slots: int
    review_days: int = 7
    min_chars: int = 0


class AssignRequest(_Camel):
    applicant_id: UUID


class CampaignItem(_Camel):
    id: UUID
    book_id: UUID
    book_title: str | None
    author_id: UUID
    slots: int
    filled: int
    remaining: int
    review_days: int
    min_chars: int
    status_cd: str
    created_at: datetime


class CampaignListResponse(_Camel):
    items: list[CampaignItem]


class ApplicationItem(_Camel):
    id: UUID
    campaign_id: UUID
    book_id: UUID
    book_title: str | None
    status_cd: str
    deadline_at: datetime | None
    created_at: datetime


class ApplicationListResponse(_Camel):
    items: list[ApplicationItem]
