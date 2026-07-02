"""신고 모델 — 스키마 `commu`.

독자/유저가 책·리뷰·계정을 신고 → 운영자(potato)가 처리. reporter 는 usr.account,
처리자(resolved_by)는 potato.operator — 두 영역을 잇는 경계 테이블.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Report(Base):
    __tablename__ = "report"
    __table_args__ = {"schema": "commu"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="SET NULL"))
    target_type = Column("target_type_cd", String(20), nullable=False)  # BOOK | REVIEW | ACCOUNT
    target_id = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column("status_cd", String(20), nullable=False, default="OPEN")  # OPEN | RESOLVED | DISMISSED
    resolution = Column(Text)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("potato.operator.id", ondelete="SET NULL"))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    resolved_at = Column("resolved_ts", DateTime(timezone=True))
