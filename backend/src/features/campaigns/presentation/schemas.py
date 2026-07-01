"""campaigns API 스키마 (camelCase)."""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class CreateCampaignRequest(CamelSchema):
    book_id: UUID
    slots: int
    review_days: int = 7
    min_chars: int = 0


class AssignRequest(CamelSchema):
    applicant_id: UUID


class CampaignItem(CamelSchema):
    id: UUID
    book_id: UUID
    book_title: str | None
    category: str | None
    author_id: UUID
    slots: int
    filled: int
    remaining: int
    review_days: int
    min_chars: int
    status_cd: str
    created_at: datetime


class CampaignListResponse(CamelSchema):
    items: list[CampaignItem]


class ApplicationItem(CamelSchema):
    id: UUID
    campaign_id: UUID
    book_id: UUID
    book_title: str | None
    status_cd: str
    deadline_at: datetime | None
    created_at: datetime


class ApplicationListResponse(CamelSchema):
    items: list[ApplicationItem]


class AuthorCampaignItem(CamelSchema):
    id: UUID
    book_id: UUID
    book_title: str | None
    slots: int
    filled: int
    remaining: int
    review_days: int
    min_chars: int
    status_cd: str
    applicants: int
    reviewed: int
    created_at: datetime


class AuthorCampaignListResponse(CamelSchema):
    items: list[AuthorCampaignItem]


class ApplicantItem(CamelSchema):
    id: UUID
    applicant_id: UUID
    applicant_name: str | None
    status_cd: str
    deadline_at: datetime | None
    created_at: datetime


class ApplicantListResponse(CamelSchema):
    items: list[ApplicantItem]


class ReviewerStatusResponse(CamelSchema):
    completed: int
    missed: int
    active: int
    pending: int
    received: int
    completion_rate: int | None
    blocked_until: datetime | None
