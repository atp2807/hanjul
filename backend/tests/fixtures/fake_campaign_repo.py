"""인메모리 CampaignRepository(campaigns 피처) — 서비스 단위 테스트용.

Protocol 구현 대상: src.features.campaigns.domain.models.CampaignRepository
  (create · get · book_author · list_open · apply · assign · list_my_applications ·
   cancel · close · list_for_author · list_applicants · mark_completed ·
   sweep_overdue · reviewer_status · block_reviewer · unblock_reviewer · blocked_until)

미작성(EXPIRED) 누적 시 자동 자격회수(MISS_LIMIT·BLOCK_DAYS)는 SqlCampaignRepository
전용 세부구현이라 여기선 재현하지 않는다 — CampaignService는 운영자 수동
block_reviewer/unblock_reviewer 경로로 자격회수를 검증한다.
"""
import uuid
from datetime import UTC, datetime
from uuid import UUID

from src.features.campaigns.domain.models import (
    ApplicantView,
    ApplicationView,
    AuthorCampaignView,
    CampaignView,
    ReviewerStatus,
)


# ── Fake 리포지토리 ──────────────────────────────────
class FakeCampaignRepository:
    def __init__(self) -> None:
        self.campaigns: dict[UUID, dict] = {}       # id -> 캠페인 필드 dict
        self.applications: dict[UUID, dict] = {}    # id -> 신청 필드 dict
        self.blocks: dict[UUID, datetime] = {}       # account_id -> 차단 만료

    # ── 테스트 준비 헬퍼 ──────────────────────────────
    def seed_campaign(
        self,
        book_id: UUID | None = None,
        author_id: UUID | None = None,
        slots: int = 3,
        filled: int = 0,
        review_days: int = 7,
        min_chars: int = 0,
        status: str = "OPEN",
        book_title: str | None = "제목",
        category: str | None = None,
    ) -> UUID:
        cid = uuid.uuid4()
        self.campaigns[cid] = dict(
            id=cid, book_id=book_id or uuid.uuid4(), book_title=book_title, category=category,
            author_id=author_id or uuid.uuid4(), slots=slots, filled=filled,
            review_days=review_days, min_chars=min_chars, status=status,
            created_at=datetime.now(UTC),
        )
        return cid

    def seed_application(
        self,
        campaign_id: UUID,
        applicant_id: UUID,
        status: str = "PENDING",
        deadline_at: datetime | None = None,
    ) -> UUID:
        aid = uuid.uuid4()
        c = self.campaigns[campaign_id]
        self.applications[aid] = dict(
            id=aid, campaign_id=campaign_id, book_id=c["book_id"], book_title=c["book_title"],
            applicant_id=applicant_id, status=status, deadline_at=deadline_at,
            assigned_at=None, created_at=datetime.now(UTC),
        )
        return aid

    # ── 뷰 변환 ───────────────────────────────────────
    def _campaign_view(self, c: dict) -> CampaignView:
        return CampaignView(
            id=c["id"], book_id=c["book_id"], book_title=c["book_title"], category=c["category"],
            author_id=c["author_id"], slots=c["slots"], filled=c["filled"],
            remaining=max(0, c["slots"] - c["filled"]), review_days=c["review_days"],
            min_chars=c["min_chars"], status=c["status"], created_at=c["created_at"],
        )

    # ── Protocol 구현 ─────────────────────────────────
    async def create(self, book_id, author_id, slots, review_days, min_chars) -> UUID:
        return self.seed_campaign(
            book_id=book_id, author_id=author_id, slots=slots, filled=0,
            review_days=review_days, min_chars=min_chars, status="OPEN",
        )

    async def get(self, campaign_id) -> CampaignView | None:
        c = self.campaigns.get(campaign_id)
        return self._campaign_view(c) if c else None

    async def book_author(self, book_id) -> UUID | None:
        for c in self.campaigns.values():
            if c["book_id"] == book_id:
                return c["author_id"]
        return None

    async def list_open(self, category: str | None = None) -> list[CampaignView]:
        rows = [c for c in self.campaigns.values() if c["status"] == "OPEN"]
        if category:
            rows = [c for c in rows if c["category"] == category]
        return [self._campaign_view(c) for c in rows]

    async def apply(self, campaign_id, applicant_id) -> None:
        for a in self.applications.values():
            if a["campaign_id"] == campaign_id and a["applicant_id"] == applicant_id:
                return  # 멱등
        self.seed_application(campaign_id, applicant_id, status="PENDING")

    async def assign(self, campaign_id, applicant_id, deadline) -> bool:
        c = self.campaigns.get(campaign_id)
        if c is None or c["filled"] >= c["slots"]:
            return False
        app = next(
            (a for a in self.applications.values()
             if a["campaign_id"] == campaign_id and a["applicant_id"] == applicant_id and a["status"] == "PENDING"),
            None,
        )
        if app is None:
            return False
        app["status"] = "ASSIGNED"
        app["deadline_at"] = deadline
        app["assigned_at"] = datetime.now(UTC)
        c["filled"] += 1
        if c["filled"] >= c["slots"]:
            c["status"] = "CLOSED"
        return True

    async def list_my_applications(self, applicant_id) -> list[ApplicationView]:
        rows = [a for a in self.applications.values() if a["applicant_id"] == applicant_id]
        rows.sort(key=lambda a: a["created_at"], reverse=True)
        return [
            ApplicationView(
                id=a["id"], campaign_id=a["campaign_id"], book_id=a["book_id"], book_title=a["book_title"],
                applicant_id=a["applicant_id"], status=a["status"], deadline_at=a["deadline_at"],
                created_at=a["created_at"],
            )
            for a in rows
        ]

    async def cancel(self, campaign_id, applicant_id) -> bool:
        app = next(
            (a for a in self.applications.values()
             if a["campaign_id"] == campaign_id and a["applicant_id"] == applicant_id and a["status"] == "PENDING"),
            None,
        )
        if app is None:
            return False
        del self.applications[app["id"]]
        return True

    async def close(self, campaign_id) -> None:
        c = self.campaigns.get(campaign_id)
        if c is not None:
            c["status"] = "CLOSED"

    async def list_for_author(self, author_id) -> list[AuthorCampaignView]:
        rows = [c for c in self.campaigns.values() if c["author_id"] == author_id]
        views = []
        for c in rows:
            apps = [a for a in self.applications.values() if a["campaign_id"] == c["id"]]
            reviewed = sum(1 for a in apps if a["status"] == "COMPLETED")
            views.append(
                AuthorCampaignView(
                    id=c["id"], book_id=c["book_id"], book_title=c["book_title"], slots=c["slots"],
                    filled=c["filled"], remaining=max(0, c["slots"] - c["filled"]), review_days=c["review_days"],
                    min_chars=c["min_chars"], status=c["status"], applicants=len(apps), reviewed=reviewed,
                    created_at=c["created_at"],
                )
            )
        return views

    async def list_applicants(self, campaign_id) -> list[ApplicantView]:
        rows = [a for a in self.applications.values() if a["campaign_id"] == campaign_id]
        rows.sort(key=lambda a: a["created_at"])
        return [
            ApplicantView(
                id=a["id"], applicant_id=a["applicant_id"], applicant_name=None,
                status=a["status"], deadline_at=a["deadline_at"], created_at=a["created_at"],
            )
            for a in rows
        ]

    async def mark_completed(self, book_id, applicant_id) -> None:
        app = next(
            (a for a in self.applications.values()
             if a["book_id"] == book_id and a["applicant_id"] == applicant_id and a["status"] == "ASSIGNED"),
            None,
        )
        if app is not None:
            app["status"] = "COMPLETED"

    async def sweep_overdue(self, applicant_id, now) -> None:
        for a in self.applications.values():
            if (
                a["applicant_id"] == applicant_id
                and a["status"] == "ASSIGNED"
                and a["deadline_at"] is not None
                and a["deadline_at"] < now
            ):
                a["status"] = "EXPIRED"

    async def reviewer_status(self, applicant_id, now) -> ReviewerStatus:
        await self.sweep_overdue(applicant_id, now)
        rows = [a for a in self.applications.values() if a["applicant_id"] == applicant_id]
        completed = sum(1 for a in rows if a["status"] == "COMPLETED")
        missed = sum(1 for a in rows if a["status"] == "EXPIRED")
        active = sum(1 for a in rows if a["status"] == "ASSIGNED")
        pending = sum(1 for a in rows if a["status"] == "PENDING")
        done = completed + missed
        rate = round(completed / done * 100) if done else None
        until = self.blocks.get(applicant_id)
        blocked = until if (until is not None and until > now) else None
        return ReviewerStatus(
            completed=completed, missed=missed, active=active, pending=pending,
            received=completed + missed + active, completion_rate=rate, blocked_until=blocked,
        )

    async def block_reviewer(self, account_id, until) -> None:
        self.blocks[account_id] = until

    async def unblock_reviewer(self, account_id) -> None:
        self.blocks.pop(account_id, None)

    async def blocked_until(self, account_id) -> datetime | None:
        return self.blocks.get(account_id)
