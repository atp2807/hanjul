"""계정/인증 모델 — 스키마 `usr`.

account = 고객(독자=작가 한 사람). credential = 소셜 신원(provider별).
운영자는 여기 없음 — 완전 분리된 potato.operator (구매 불가, 별도 인증).
provider_cd 로 나라별 소셜(GOOGLE/NAVER/KAKAO/LINE/APPLE…)을 스키마 변경 없이 확장.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "account"
    __table_args__ = {"schema": "usr"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True)  # 소셜이 이메일 미제공 가능 → nullable
    display_name = Column(String(200))
    bio = Column(Text)  # 작가 소개(프로필)
    role_cd = Column(String(20), nullable=False, default="READER")   # READER | AUTHOR (운영자는 potato.operator)
    status_cd = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE | SUSPENDED
    review_blocked_at = Column("review_blocked_ts", DateTime(timezone=True))  # 서평단 자격회수: 이 시각까지 신청 제한(NULL=정상)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    credentials = relationship("Credential", back_populates="account", cascade="all, delete-orphan")


class Credential(Base):
    """소셜 신원 ↔ account 매핑. (provider_cd, provider_user_id) 유일."""
    __tablename__ = "credential"
    __table_args__ = (
        UniqueConstraint("provider_cd", "provider_user_id", name="uq_credential_provider_user"),
        {"schema": "usr"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    provider_cd = Column(String(20), nullable=False)        # GOOGLE | NAVER | KAKAO | LINE | APPLE
    provider_user_id = Column(String(255), nullable=False)  # provider 의 안정적 사용자 식별자(sub)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)

    account = relationship("Account", back_populates="credentials")
