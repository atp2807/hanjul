"""정본(canonical) 데이터 모델 — 책의 단일 진실 소스.

스키마 `pub` (publishing). 책 1—* 장(chapter) 1—* 블록(block).
블록은 HTML 조각을 담는다 — 입력(TXT/MD/DOCX…)을 정본 HTML로 변환해 저장하고,
프론트 Pretext가 이 HTML을 읽어 페이지네이션한다.

네이밍룰: Python 속성=친화명 / DB 컬럼=접미어(_ts, _cd, _no, _yn). 단수 테이블 + 스키마.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Book(Base):
    __tablename__ = "book"
    __table_args__ = {"schema": "pub"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))
    # 책 소개(시놉시스). 스토어 상세·ONIX 피드에 노출.
    description = Column(Text)
    # 분류 — 소설 | 에세이 | 시 | 자기계발 | ... (자유 코드). 스토어 탐색/필터용.
    category = Column("category_cd", String(40))
    # 콘텐츠 종류 — BOOK(일반서적) | WEBNOVEL(웹소설)
    kind = Column("kind_cd", String(20), nullable=False, default="BOOK")
    # 원어 — ko | en | ja ...
    language = Column("language_cd", String(10), nullable=False, default="ko")
    # 출판 상태 — DRAFT | REVIEW | PUBLISHED
    status = Column("status_cd", String(20), nullable=False, default="DRAFT")
    cover_url = Column(String(1000))
    isbn = Column(String(20))
    # 무료 미리보기로 공개할 블록 수 (미구매 독자 유입). 기본 3.
    preview_limit = Column("preview_block_cnt", Integer, nullable=False, default=3)
    # 판매가 (원 단위 정수). 출판 전엔 NULL 가능.
    price_amt = Column(Numeric(15, 0))
    # 기간 할인가 + 종료시각. discount_until 이 미래면 할인가가 유효가.
    discount_amt = Column(Numeric(15, 0))
    discount_until = Column("discount_until_ts", DateTime(timezone=True))
    # 출판(게시) 시각. NULL = 미출판.
    published_at = Column("published_ts", DateTime(timezone=True))
    # 운영자 강제 비공개(takedown) 시각. NULL = 정상. 작가 status와 직교 — 재출판해도 안 풀림.
    blocked_at = Column("blocked_ts", DateTime(timezone=True))
    # 예약발행 시각. 스케줄러가 이 시각 지나면 자동 게시. NULL = 예약 없음.
    scheduled_publish_at = Column("scheduled_publish_ts", DateTime(timezone=True))
    # 작가 = usr.account (role_cd=AUTHOR). 미배정 책 허용 위해 nullable.
    author_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="SET NULL"))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    chapters = relationship(
        "Chapter",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Chapter.order_no",
    )


class Chapter(Base):
    __tablename__ = "chapter"
    __table_args__ = {"schema": "pub"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500))
    # 책 내 장 순서 (0-based)
    order_no = Column(Integer, nullable=False, default=0)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    book = relationship("Book", back_populates="chapters")
    blocks = relationship(
        "Block",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Block.order_no",
    )


class Block(Base):
    """정본의 최소 단위 = HTML 조각. 버전관리 diff와 블록 에디터의 단위이기도 하다."""
    __tablename__ = "block"
    __table_args__ = {"schema": "pub"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("pub.chapter.id", ondelete="CASCADE"), nullable=False)
    # 장 내 블록 순서 (0-based)
    order_no = Column(Integer, nullable=False, default=0)
    # 블록 종류 — P(문단) | H1 | H2 | H3 | QUOTE | IMG | HR
    block_type = Column("block_type_cd", String(10), nullable=False, default="P")
    # 정본 HTML 조각 (예: "<p>첫 문장.</p>")
    html = Column(Text, nullable=False, default="")
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    chapter = relationship("Chapter", back_populates="blocks")
