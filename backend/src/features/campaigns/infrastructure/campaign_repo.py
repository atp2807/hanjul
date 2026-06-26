"""CampaignRepository 의 SQLAlchemy 구현."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.campaigns.domain.models import ApplicationView, CampaignView
from src.infrastructure.db.models.book import Book
from src.infrastructure.db.models.campaign import ReviewApplication, ReviewCampaign


def _campaign_view(c: ReviewCampaign, title: str | None) -> CampaignView:
    return CampaignView(
        id=c.id, book_id=c.book_id, book_title=title, author_id=c.author_id,
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
                select(ReviewCampaign, Book.title)
                .outerjoin(Book, Book.id == ReviewCampaign.book_id)
                .where(ReviewCampaign.id == campaign_id)
            )
        ).one_or_none()
        return _campaign_view(row[0], row[1]) if row else None

    async def book_author(self, book_id) -> UUID | None:
        return (await self.session.execute(select(Book.author_id).where(Book.id == book_id))).scalar_one_or_none()

    async def list_open(self) -> list[CampaignView]:
        rows = (
            await self.session.execute(
                select(ReviewCampaign, Book.title)
                .outerjoin(Book, Book.id == ReviewCampaign.book_id)
                .where(ReviewCampaign.status_cd == "OPEN")
                .order_by(ReviewCampaign.created_at.desc())
            )
        ).all()
        return [_campaign_view(c, t) for c, t in rows]

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
        if camp is None or camp.filled >= camp.slots or camp.status_cd != "OPEN":
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
        from datetime import datetime, timezone
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
