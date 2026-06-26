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
    status_cd: str       # PENDING | ASSIGNED | COMPLETED
    deadline_at: datetime | None
    created_at: datetime


@dataclass
class AuthorCampaignView:
    """캠페인 관리(작가 대시보드)용 — 캠페인 + 신청/리뷰 집계."""
    id: UUID
    book_id: UUID
    book_title: str | None
    slots: int
    filled: int
    remaining: int
    review_days: int
    min_chars: int
    status_cd: str
    applicants: int      # 총 신청자 수
    reviewed: int        # 리뷰 완료(COMPLETED) 수
    created_at: datetime


@dataclass
class ApplicantView:
    """캠페인 신청자 한 명 — 배정 UI용."""
    id: UUID
    applicant_id: UUID
    applicant_name: str | None
    status_cd: str
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

    async def cancel(self, campaign_id: UUID, applicant_id: UUID) -> bool:
        """신청 취소 — PENDING 신청만 삭제. 성공 True."""
        ...

    async def list_for_author(self, author_id: UUID) -> list["AuthorCampaignView"]:
        """작가 본인 캠페인 + 집계."""
        ...

    async def list_applicants(self, campaign_id: UUID) -> list["ApplicantView"]:
        """캠페인 신청자 목록(배정용)."""
        ...

    async def mark_completed(self, book_id: UUID, applicant_id: UUID) -> None:
        """그 책 캠페인의 ASSIGNED 신청을 COMPLETED 로(리뷰 작성 시). 멱등."""
        ...
