"""campaigns 도메인 — 서평단 캠페인/신청 뷰 + 리포지토리 포트."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class CampaignView:
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


@dataclass
class ApplicationView:
    id: UUID
    campaign_id: UUID
    book_id: UUID
    book_title: str | None
    applicant_id: UUID
    status_cd: str       # PENDING | ASSIGNED
    deadline_at: datetime | None
    created_at: datetime


class CampaignNotFound(Exception):
    ...


class NoSlotsLeft(Exception):
    ...


class CampaignRepository(Protocol):
    async def create(self, book_id: UUID, author_id: UUID, slots: int, review_days: int, min_chars: int) -> UUID:
        ...

    async def get(self, campaign_id: UUID) -> CampaignView | None:
        ...

    async def book_author(self, book_id: UUID) -> UUID | None:
        ...

    async def list_open(self) -> list[CampaignView]:
        ...

    async def apply(self, campaign_id: UUID, applicant_id: UUID) -> None:
        """신청(멱등). PENDING 생성."""
        ...

    async def assign(self, campaign_id: UUID, applicant_id: UUID, deadline) -> bool:
        """배정 — 슬롯 남았고 신청 PENDING이면 ASSIGNED + filled+1. 성공 True."""
        ...

    async def list_my_applications(self, applicant_id: UUID) -> list[ApplicationView]:
        ...
