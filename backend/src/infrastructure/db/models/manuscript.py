"""원고 백업 ORM — 스키마 `ms` (manuscript 피처 소유, P1 슬라이스7).

manuscript_book = 데스크탑 book.sync_key 를 여기 sync_key(UNIQUE)로 잇는 백업 전용
엔티티(pub.book 과 무관 — 발행은 books 피처, 백업은 이 스키마). manuscript_revision 은
append-only(챕터별 저장 이력, content_hash 로 dedup) — prune 외에는 삭제하지 않는다.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class ManuscriptBook(Base):
    __tablename__ = "manuscript_book"
    __table_args__ = {"schema": "ms"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    # 데스크탑이 생성하는 안정 식별자 — 로컬 자동증분 id 와 무관, 재설치/재발행에도 불변.
    sync_key = Column(UUID(as_uuid=True), nullable=False, unique=True)
    title = Column(Text, nullable=False)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class ManuscriptRevision(Base):
    """append-only — 챕터 1개의 저장 시점 스냅샷. UPDATE 없음(prune 만 DELETE)."""
    __tablename__ = "manuscript_revision"
    __table_args__ = {"schema": "ms"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("ms.manuscript_book.id", ondelete="CASCADE"), nullable=False)
    # 데스크탑 챕터 식별자를 문자열로(로컬 INTEGER id 를 str() 한 값 — 서버는 의미 해석 안 함).
    chapter_key = Column(Text, nullable=False)
    chapter_title = Column(Text, nullable=False)
    html = Column(Text, nullable=False)
    # sha256(html) 클라 계산값 — 서버 재검증 없음(도메인 모델 docstring 참고).
    content_hash = Column(Text, nullable=False)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
