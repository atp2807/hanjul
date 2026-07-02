"""campaigns 서비스 — 서평단 캠페인 생성·신청·배정(증정본 지급)."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.features.campaigns.domain.models import (
    OPERATOR_BLOCK_DAYS,
    ApplicantView,
    ApplicationView,
    AuthorCampaignView,
    CampaignNotFound,
    CampaignRepository,
    CampaignView,
    NoSlotsLeft,
    ReviewerBlocked,
    ReviewerStatus,
)
from src.shared.errors import ValidationError


class CampaignService:
    def __init__(self, repo: CampaignRepository):
        self.repo = repo

    async def create(self, book_id: UUID, author_id: UUID, slots: int, review_days: int = 7, min_chars: int = 0) -> UUID:
        if slots < 1:
            raise ValidationError("증정본은 1부 이상")
        return await self.repo.create(book_id, author_id, slots, review_days, min_chars)

    async def list_open(self, category: str | None = None) -> list[CampaignView]:
        return await self.repo.list_open(category)

    async def get(self, campaign_id: UUID) -> CampaignView:
        c = await self.repo.get(campaign_id)
        if c is None:
            raise CampaignNotFound(campaign_id)
        return c

    async def apply(self, campaign_id: UUID, applicant_id: UUID, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        # 기한 초과분 정리 후 자격회수 상태면 신청 차단
        status = await self.repo.reviewer_status(applicant_id, now)
        if status.blocked_until is not None:
            raise ReviewerBlocked(status.blocked_until)
        c = await self.get(campaign_id)
        if c.status != "OPEN":
            raise NoSlotsLeft()
        await self.repo.apply(campaign_id, applicant_id)

    async def assign(self, campaign_id: UUID, applicant_id: UUID, now: datetime | None = None) -> bool:
        """배정 — 슬롯 차감 + 마감 설정. 증정본 지급은 호출 측(엔드포인트)이 OrderService로."""
        c = await self.get(campaign_id)
        now = now or datetime.now(UTC)
        deadline = now + timedelta(days=c.review_days)
        ok = await self.repo.assign(campaign_id, applicant_id, deadline)
        if not ok:
            raise NoSlotsLeft()
        return True

    async def list_my_applications(self, applicant_id: UUID, now: datetime | None = None) -> list[ApplicationView]:
        await self.repo.sweep_overdue(applicant_id, now or datetime.now(UTC))
        return await self.repo.list_my_applications(applicant_id)

    async def reviewer_status(self, applicant_id: UUID, now: datetime | None = None) -> ReviewerStatus:
        return await self.repo.reviewer_status(applicant_id, now or datetime.now(UTC))

    # ── 운영자 자격회수(서평단) ───────────────────────
    async def block_reviewer(self, account_id: UUID, now: datetime | None = None) -> None:
        """운영자 수동 자격회수 — 해제 전까지 사실상 무기한(far-future)."""
        now = now or datetime.now(UTC)
        await self.repo.block_reviewer(account_id, now + timedelta(days=OPERATOR_BLOCK_DAYS))

    async def unblock_reviewer(self, account_id: UUID) -> None:
        await self.repo.unblock_reviewer(account_id)

    async def reviewer_blocked_until(
        self, account_id: UUID, now: datetime | None = None
    ) -> datetime | None:
        """현재 유효한 차단 만료 시각(만료됐으면 None)."""
        now = now or datetime.now(UTC)
        until = await self.repo.blocked_until(account_id)
        return until if (until is not None and until > now) else None

    async def cancel(self, campaign_id: UUID, applicant_id: UUID) -> bool:
        """신청 취소 — PENDING 만. 이미 배정됐으면 False."""
        return await self.repo.cancel(campaign_id, applicant_id)

    async def close(self, campaign_id: UUID) -> None:
        """모집 수동 마감."""
        await self.repo.close(campaign_id)

    async def list_for_author(self, author_id: UUID) -> list[AuthorCampaignView]:
        return await self.repo.list_for_author(author_id)

    async def list_applicants(self, campaign_id: UUID) -> list[ApplicantView]:
        return await self.repo.list_applicants(campaign_id)

    async def mark_review_done(self, book_id: UUID, applicant_id: UUID) -> None:
        """증정본 리뷰 작성 시 호출 — 배정 신청을 COMPLETED 로(완료율 집계)."""
        await self.repo.mark_completed(book_id, applicant_id)
