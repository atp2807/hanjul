"""팔로우 + 알림 모델 — 스키마 commu.

follow = 독자→작가 구독(쌍 유일). notification = 수신자별 인앱 알림,
(수신자,책,종류) 유일 → 같은 책 재발행 시 알림 중복 안 됨(멱등).
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Follow(Base):
    __tablename__ = "follow"
    __table_args__ = (UniqueConstraint("follower_id", "author_id", name="uq_follow_pair"), {"schema": "commu"})

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        UniqueConstraint("recipient_id", "book_id", "kind_cd", name="uq_notification_recipient_book_kind"),
        {"schema": "commu"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    kind = Column("kind_cd", String(20), nullable=False)  # NEW_BOOK
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="CASCADE"))
    title = Column(Text)
    is_read = Column("read_yn", Boolean, nullable=False, default=False, server_default=false())
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
