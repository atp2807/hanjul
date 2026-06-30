"""CampaignRepository 의 SQLAlchemy 구현."""
from uuid import UUID

from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timedelta, timezone


def _aware(dt):
    """sqlite는 tz-naive로 돌려줌 → UTC로 간주해 aware 비교 가능하게."""
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt

from src.features.campaigns.domain.models import (
    BLOCK_DAYS,
    MISS_LIMIT,
    ApplicantView,
    ApplicationView,
    AuthorCampaignView,
    CampaignView,
    ReviewerStatus,
)
from src.infrastructure.db.models.account import Account
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.campaign import ReviewApplication, ReviewCampaign


def _campaign_view(c: ReviewCampaign, title: str | None, category: str | None = None) -> CampaignView:
    return CampaignView(
        id=c.id, book_id=c.book_id, book_title=title, category=category, author_id=c.author_id,
        slots=c.slots, filled=c.filled, remaining=max(0, c.slots - c.filled),
        review_days=c.review_days, min_chars=c.min_chars, status_cd=c.status_cd, created_at=c.created_at,
    )


class SqlCampaignRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, book_id, author_id, slots, review_days, min_chars) -> UUID:
        c = ReviewCampaign(book_id=book_id, author_id=author_id, slots=slots, review_days=review_days, min_chars=min_chars)
        self.session.add(c)
        await self.session.commit()
        return c.id

    async def get(self, campaign_id) -> CampaignView | None:
        row = (
            await self.session.execute(
                select(ReviewCampaign, Book.title, Book.category)
                .outerjoin(Book, Book.id == ReviewCampaign.book_id)
                .where(ReviewCampaign.id == campaign_id)
            )
        ).one_or_none()
        return _campaign_view(row[0], row[1], row[2]) if row else None

    async def book_author(self, book_id) -> UUID | None:
        return (await self.session.execute(select(Book.author_id).where(Book.id == book_id))).scalar_one_or_none()

    async def list_open(self, category: str | None = None) -> list[CampaignView]:
        q = (
            select(ReviewCampaign, Book.title, Book.category)
            .outerjoin(Book, Book.id == ReviewCampaign.book_id)
            .where(ReviewCampaign.status_cd == "OPEN")
        )
        if category:
            q = q.where(Book.category == category)
        rows = (await self.session.execute(q.order_by(ReviewCampaign.created_at.desc()))).all()
        return [_campaign_view(c, t, cat) for c, t, cat in rows]

    async def apply(self, campaign_id, applicant_id) -> None:
        exists = (
            await self.session.execute(
                select(ReviewApplication.id).where(
                    ReviewApplication.campaign_id == campaign_id,
                    ReviewApplication.applicant_id == applicant_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            return
        self.session.add(ReviewApplication(campaign_id=campaign_id, applicant_id=applicant_id))
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()  # 경쟁 → 멱등

    async def assign(self, campaign_id, applicant_id, deadline) -> bool:
        # 캠페인 행 잠금 → 슬롯 확인 + 신청 PENDING → ASSIGNED + filled+1
        camp = (
            await self.session.execute(
                select(ReviewCampaign).where(ReviewCampaign.id == campaign_id).with_for_update()
            )
        ).scalar_one_or_none()
        # 슬롯만 게이트 — 수동 마감(CLOSED·슬롯 남음)된 캠페인도 기존 신청자는 배정 가능
        if camp is None or camp.filled >= camp.slots:
            await self.session.rollback()
            return False
        app = (
            await self.session.execute(
                select(ReviewApplication).where(
                    ReviewApplication.campaign_id == campaign_id,
                    ReviewApplication.applicant_id == applicant_id,
                    ReviewApplication.status_cd == "PENDING",
                ).with_for_update()
            )
        ).scalar_one_or_none()
        if app is None:
            await self.session.rollback()
            return False
        app.status_cd = "ASSIGNED"
        app.deadline_at = deadline
        app.assigned_at = datetime.now(timezone.utc)
        camp.filled += 1
        if camp.filled >= camp.slots:
            camp.status_cd = "CLOSED"
        await self.session.commit()
        return True

    async def list_my_applications(self, applicant_id) -> list[ApplicationView]:
        rows = (
            await self.session.execute(
                select(ReviewApplication, ReviewCampaign.book_id, Book.title)
                .join(ReviewCampaign, ReviewCampaign.id == ReviewApplication.campaign_id)
                .outerjoin(Book, Book.id == ReviewCampaign.book_id)
                .where(ReviewApplication.applicant_id == applicant_id)
                .order_by(ReviewApplication.created_at.desc())
            )
        ).all()
        return [
            ApplicationView(
                id=a.id, campaign_id=a.campaign_id, book_id=book_id, book_title=title,
                applicant_id=a.applicant_id, status_cd=a.status_cd, deadline_at=a.deadline_at, created_at=a.created_at,
            )
            for a, book_id, title in rows
        ]

    async def close(self, campaign_id) -> None:
        """모집 수동 마감 — status CLOSED (피드 제외 + 새 신청 차단)."""
        camp = (
            await self.session.execute(select(ReviewCampaign).where(ReviewCampaign.id == campaign_id))
        ).scalar_one_or_none()
        if camp is not None:
            camp.status_cd = "CLOSED"
            await self.session.commit()

    async def cancel(self, campaign_id, applicant_id) -> bool:
        app = (
            await self.session.execute(
                select(ReviewApplication).where(
                    ReviewApplication.campaign_id == campaign_id,
                    ReviewApplication.applicant_id == applicant_id,
                    ReviewApplication.status_cd == "PENDING",
                )
            )
        ).scalar_one_or_none()
        if app is None:
            return False
        await self.session.delete(app)
        await self.session.commit()
        return True

    async def list_for_author(self, author_id) -> list[AuthorCampaignView]:
        # 캠페인별 신청자 수 / 완료 수 서브쿼리 집계
        app_count = (
            select(
                ReviewApplication.campaign_id.label("cid"),
                func.count().label("applicants"),
                func.sum(case((ReviewApplication.status_cd == "COMPLETED", 1), else_=0)).label("reviewed"),
            )
            .group_by(ReviewApplication.campaign_id)
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(ReviewCampaign, Book.title, app_count.c.applicants, app_count.c.reviewed)
                .outerjoin(Book, Book.id == ReviewCampaign.book_id)
                .outerjoin(app_count, app_count.c.cid == ReviewCampaign.id)
                .where(ReviewCampaign.author_id == author_id)
                .order_by(ReviewCampaign.created_at.desc())
            )
        ).all()
        return [
            AuthorCampaignView(
                id=c.id, book_id=c.book_id, book_title=title, slots=c.slots, filled=c.filled,
                remaining=max(0, c.slots - c.filled), review_days=c.review_days, min_chars=c.min_chars,
                status_cd=c.status_cd, applicants=applicants or 0, reviewed=reviewed or 0, created_at=c.created_at,
            )
            for c, title, applicants, reviewed in rows
        ]

    async def list_applicants(self, campaign_id) -> list[ApplicantView]:
        # 이름은 합성루트(엔드포인트)가 accounts.names_for로 해석 — usr.account 직접 JOIN 안 함.
        rows = (
            await self.session.execute(
                select(ReviewApplication)
                .where(ReviewApplication.campaign_id == campaign_id)
                .order_by(ReviewApplication.created_at.asc())
            )
        ).scalars().all()
        return [
            ApplicantView(
                id=a.id, applicant_id=a.applicant_id, applicant_name=None,
                status_cd=a.status_cd, deadline_at=a.deadline_at, created_at=a.created_at,
            )
            for a in rows
        ]

    async def due_soon(self, now, within_days) -> list[tuple]:
        """기한이 (now, now+within_days] 인 ASSIGNED 신청 — (리뷰어, 책, 제목)."""
        cutoff = now + timedelta(days=within_days)
        rows = (
            await self.session.execute(
                select(ReviewApplication.applicant_id, ReviewCampaign.book_id, Book.title)
                .join(ReviewCampaign, ReviewCampaign.id == ReviewApplication.campaign_id)
                .outerjoin(Book, Book.id == ReviewCampaign.book_id)
                .where(
                    ReviewApplication.status_cd == "ASSIGNED",
                    ReviewApplication.deadline_at.is_not(None),
                    ReviewApplication.deadline_at > now,
                    ReviewApplication.deadline_at <= cutoff,
                )
            )
        ).all()
        return [(r[0], r[1], r[2]) for r in rows]

    async def mark_completed(self, book_id, applicant_id) -> None:
        app = (
            await self.session.execute(
                select(ReviewApplication)
                .join(ReviewCampaign, ReviewCampaign.id == ReviewApplication.campaign_id)
                .where(
                    ReviewCampaign.book_id == book_id,
                    ReviewApplication.applicant_id == applicant_id,
                    ReviewApplication.status_cd == "ASSIGNED",
                )
                .order_by(ReviewApplication.assigned_at.asc())  # 다중 캠페인 시 가장 먼저 배정된 것부터(결정적)
            )
        ).scalars().first()
        if app is None:
            return
        app.status_cd = "COMPLETED"
        await self.session.commit()

    async def sweep_overdue(self, applicant_id, now) -> None:
        # 기한 초과 ASSIGNED → EXPIRED
        overdue = (
            await self.session.execute(
                select(ReviewApplication).where(
                    ReviewApplication.applicant_id == applicant_id,
                    ReviewApplication.status_cd == "ASSIGNED",
                    ReviewApplication.deadline_at.is_not(None),
                    ReviewApplication.deadline_at < now,
                )
            )
        ).scalars().all()
        if not overdue:
            return
        for a in overdue:
            a.status_cd = "EXPIRED"
        await self.session.flush()  # EXPIRED 반영 후 집계
        acc = (await self.session.execute(select(Account).where(Account.id == applicant_id))).scalar_one_or_none()
        blocked_at = _aware(acc.review_blocked_at) if (acc is not None and acc.review_blocked_at is not None) else None
        # 차단 중이면 그대로 두고, 비차단일 때만 '이번 사이클' 미작성으로 재판정.
        if acc is not None and (blocked_at is None or blocked_at <= now):
            # 직전 차단 이후(=차단설정시각 = blocked_at - BLOCK_DAYS) 발생한 미작성만 카운트 → 회복 후 리셋
            cond = [
                ReviewApplication.applicant_id == applicant_id,
                ReviewApplication.status_cd == "EXPIRED",
            ]
            if blocked_at is not None:
                cond.append(ReviewApplication.deadline_at > blocked_at - timedelta(days=BLOCK_DAYS))
            cycle_missed = (
                await self.session.execute(select(func.count()).select_from(ReviewApplication).where(*cond))
            ).scalar_one()
            if cycle_missed >= MISS_LIMIT:
                acc.review_blocked_at = now + timedelta(days=BLOCK_DAYS)
        await self.session.commit()

    async def reviewer_status(self, applicant_id, now) -> ReviewerStatus:
        await self.sweep_overdue(applicant_id, now)
        rows = (
            await self.session.execute(
                select(ReviewApplication.status_cd, func.count())
                .where(ReviewApplication.applicant_id == applicant_id)
                .group_by(ReviewApplication.status_cd)
            )
        ).all()
        by = {s: n for s, n in rows}
        completed, missed = by.get("COMPLETED", 0), by.get("EXPIRED", 0)
        active, pending = by.get("ASSIGNED", 0), by.get("PENDING", 0)
        done = completed + missed
        rate = round(completed / done * 100) if done else None
        acc = (await self.session.execute(select(Account.review_blocked_at).where(Account.id == applicant_id))).scalar_one_or_none()
        acc = _aware(acc)
        blocked = acc if (acc is not None and acc > now) else None
        return ReviewerStatus(
            completed=completed, missed=missed, active=active, pending=pending,
            received=completed + missed + active, completion_rate=rate, blocked_until=blocked,
        )
