"""운영자 모델 — 스키마 `potato` (고객 usr.account 와 완전 분리된 인증 영역).

operator = 내부 직원(운영자/개발자). 고객처럼 소셜가입·구매 불가.
  role_cd: OPERATOR(신뢰·안전) | DEVELOPER(+ 시스템/엔진 메뉴).
audit_log = 운영자 행위 감사(누가·언제·무엇을·어떤 대상).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Operator(Base):
    __tablename__ = "operator"
    __table_args__ = {"schema": "potato"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(200), nullable=False)
    role_cd = Column(String(20), nullable=False, default="OPERATOR")  # OPERATOR | DEVELOPER
    is_active = Column("active_yn", Boolean, nullable=False, default=True)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)


class AuditLog(Base):
    """운영자 행위 감사 — 모든 집행/변경에 1건씩 (operator_id·IP 자동 캡처)."""
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "potato"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("potato.operator.id", ondelete="SET NULL"))
    action = Column(String(40), nullable=False)       # TAKEDOWN | APPROVE | REJECT | SUSPEND | ...
    entity_type = Column(String(40), nullable=False)  # BOOK | ACCOUNT | REVIEW | REPORT
    entity_id = Column(UUID(as_uuid=True))
    detail = Column(JSON().with_variant(JSONB, "postgresql"))  # reason / old·new 등
    ip = Column(String(64))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
