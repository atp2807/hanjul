"""서평단 캠페인 모델 — 스키마 commu.

review_campaign = 작가/출판사가 책에 건 서평단(증정본 N부).
review_application = 독자의 리뷰어 신청(배정되면 증정본 + 마감).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewCampaign(Base):
    __tablename__ = "review_campaign"
    __table_args__ = {"schema": "commu"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    slots = Column(Integer, nullable=False)
    filled = Column(Integer, nullable=False, default=0)
    review_days = Column(Integer, nullable=False, default=7)
    min_chars = Column(Integer, nullable=False, default=0)
    status_cd = Column(String(20), nullable=False, default="OPEN")  # OPEN | CLOSED
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)


class ReviewApplication(Base):
    __tablename__ = "review_application"
    __table_args__ = (
        UniqueConstraint("campaign_id", "applicant_id", name="uq_application_campaign_applicant"),
        {"schema": "commu"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("commu.review_campaign.id", ondelete="CASCADE"), nullable=False)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    status_cd = Column(String(20), nullable=False, default="PENDING")  # PENDING | ASSIGNED
    assigned_at = Column("assigned_ts", DateTime(timezone=True))
    deadline_at = Column("deadline_ts", DateTime(timezone=True))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
