"""한줄독(구 juldoc) 문서 도메인 ORM — 스키마 `doc`.

juldoc 의 asyncpg raw SQL 저장소를 hanjul SQLAlchemy async 로 이식한 것의 ORM 층.
마이그레이션 0025(doc.document / doc.share_link)와 정확히 일치한다.

네이밍룰: Python 속성=친화명(title/format/created_at…) / DB 컬럼=접미어(Column("format_cd"),
Column("created_ts")…). owner_id 는 hanjul usr.account(id) FK — NULL 이면 공용(ownerless).
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    """정본 HTML 문서 1건. 정본(canonical) = engine dialect.serialize_doc 산출.

    owner_id NULL = ownerless(무인증 생성, 종전 개방 동작) / 값 존재 = 잠김(소유자만 변경).
    deleted_ts = soft delete (NULL = 살아있음).
    """
    __tablename__ = "document"
    __table_args__ = {"schema": "doc"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False, default="")
    # 원본 포맷 코드 — md | html | docx | pdf | hwp ... (upload 시 판정).
    format = Column("format_cd", Text, nullable=False, default="")
    # 정본 HTML — <article data-juldoc="1"> 래퍼 포함.
    html = Column(Text, nullable=False)
    # 업로드 원본 바이트의 sha256(hex). 빈 문서는 NULL.
    source_hash = Column(Text)
    # 소유자 = usr.account.id. NULL = ownerless(공용).
    owner_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id"))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(
        "updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    # soft delete 시각. NULL = 살아있음.
    deleted_at = Column("deleted_ts", DateTime(timezone=True))


class ShareLink(Base):
    """문서 공개 공유 링크. token 이 곧 접근 자격 — capability(VIEW/EDIT/EXPORT)로 권한 분기.

    revoked_ts = 회수 시각(정본은 DB 레코드). NULL 이 아니면 회수됨(재활성화 없음).
    """
    __tablename__ = "share_link"
    __table_args__ = {"schema": "doc"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("doc.document.id"), nullable=False
    )
    token = Column(Text, nullable=False, unique=True)
    # 권한 코드 — view | edit | export (친화 소문자, Capability StrEnum 값 그대로).
    capability = Column("capability_cd", Text, nullable=False)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    # 회수 시각. NULL = 유효.
    revoked_at = Column("revoked_ts", DateTime(timezone=True))
