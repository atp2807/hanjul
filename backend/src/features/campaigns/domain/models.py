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
    category: str | None
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


@dataclass
class ReviewerStatus:
    """리뷰어 신뢰도·자격 — 내 활동 상단/요소 카드용."""
    completed: int       # 기한 내 완료
    missed: int          # 기한 초과 미작성(EXPIRED)
    active: int          # 진행 중(ASSIGNED)
    pending: int         # 신청 대기
    received: int        # 받은 증정본(배정된 적 있는 총합)
    completion_rate: int | None  # 완료/(완료+미작성) %, 이력 없으면 None
    blocked_until: datetime | None  # 자격회수 해제 시각(없으면 정상)


# 자격회수 룰: 미작성(EXPIRED) 2회 누적 시 14일 신청 제한.
MISS_LIMIT = 2
BLOCK_DAYS = 14
# 운영자 수동 자격회수 = 해제 전까지 사실상 무기한.
OPERATOR_BLOCK_DAYS = 3650


class CampaignNotFound(Exception):
    ...


class NoSlotsLeft(Exception):
    ...


class ReviewerBlocked(Exception):
    """자격회수 기간 중 신청 시도."""
    def __init__(self, until):
        self.until = until


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

    async def close(self, campaign_id: UUID) -> None:
        """모집 수동 마감(status CLOSED)."""
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

    async def sweep_overdue(self, applicant_id: UUID, now: datetime) -> None:
        """기한 초과 ASSIGNED → EXPIRED. 누적 미작성이 한계 도달 시 자격회수 설정."""
        ...

    async def reviewer_status(self, applicant_id: UUID, now: datetime) -> "ReviewerStatus":
        """리뷰어 신뢰도·자격 집계(sweep 후)."""
        ...

    async def block_reviewer(self, account_id: UUID, until: datetime) -> None:
        """운영자 수동 자격회수 — commu.reviewer_block upsert."""
        ...

    async def unblock_reviewer(self, account_id: UUID) -> None:
        """자격회수 해제 — 차단 행 삭제."""
        ...

    async def blocked_until(self, account_id: UUID) -> datetime | None:
        """현재 차단 만료 시각(없으면 None) — 만료 필터는 호출 측."""
        ...
