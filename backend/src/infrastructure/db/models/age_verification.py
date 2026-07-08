"""성인인증 요청 모델 — 스키마 `usr` (age_verification 피처 소유).

신분증 사진 업로드 → potato 운영자 승인/거부. id_photo_key는 심사 완료 즉시(애플리케이션
레이어가) NULL로 되돌리고 원본 파일도 삭제한다 — 심사 목적 외 PII 보관 금지 방침.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AgeVerificationRequest(Base):
    __tablename__ = "age_verification_request"
    __table_args__ = {"schema": "usr"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    # 신분증 사진(비공개 스토리지) 키. 심사완료 즉시 NULL(원본도 삭제) — 목적 외 보관 금지.
    id_photo_key = Column(String(255), nullable=True)
    status = Column("status_cd", String(20), nullable=False, default="PENDING")  # PENDING | APPROVED | REJECTED
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("potato.operator.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column("reviewed_ts", DateTime(timezone=True), nullable=True)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
