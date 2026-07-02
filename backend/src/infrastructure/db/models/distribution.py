"""서점 배포 기록 — 스키마 `dist`.

책을 어느 서점 채널로 보냈고 결과가 어땠는지 추적.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Distribution(Base):
    __tablename__ = "distribution"
    __table_args__ = {"schema": "dist"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False)
    channel_cd = Column(String(20), nullable=False)   # KYOBO | YES24 | ALADIN | DEMO ...
    status_cd = Column(String(20), nullable=False)    # SENT | FAILED
    message = Column(Text)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
