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


class ReviewerBlock(Base):
    """서평단 자격회수 — 이 시각까지 신청 제한. (자동: 미작성 누적 / 수동: 운영자)

    이전엔 usr.account.review_blocked_ts 였으나 서평단(commu) 개념이라 이리로 이전(0021).
    행 존재 + blocked_until > now 이면 차단. 해제 = 행 삭제.
    """
    __tablename__ = "reviewer_block"
    __table_args__ = {"schema": "commu"}

    account_id = Column(
        UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_until = Column("blocked_until_ts", DateTime(timezone=True), nullable=False)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
