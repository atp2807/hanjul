"""리뷰·평점 모델 — 스키마 commu. 책 1—* 리뷰, (책,계정) 유일."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Review(Base):
    __tablename__ = "review"
    __table_args__ = (UniqueConstraint("book_id", "account_id", name="uq_review_book_account"), {"schema": "commu"})

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1~5
    body = Column(Text)
    source = Column("source_cd", String(20), nullable=False, default="PURCHASE")  # PURCHASE | REVIEW_COPY(서평단)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    # 재작성(upsert update) 시 갱신. 최초 작성 땐 NULL → '수정됨' 미표시.
    updated_at = Column("updated_ts", DateTime(timezone=True), onupdate=_now)
