"""원천징수 신고 대상 — 스키마 `bill` (woncheon 커넥터 피처 소유, lr-ac61f505 스켈레톤).

지급(payout) 시점·원천징수 대상 작가만 최소수집하는 별도 테이블 — bill.bank_account
(계좌등록)과는 다른 관심사(과잉수집 금지). 주민등록번호는 평문 저장하지 않고 Fernet
암호화(payouts.application.crypto 와 같은 키 관리 패턴 재사용) 저장.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class WithholdingSubject(Base):
    """payout 1건당 원천징수 신고에 필요한 최소 개인정보(주민번호 암호문 + 소득구분)."""
    __tablename__ = "withholding_subject"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payout_id = Column(UUID(as_uuid=True), ForeignKey("bill.payout.id", ondelete="CASCADE"), nullable=False)
    resident_no_enc = Column(String(255), nullable=False)  # Fernet 암호문 — 평문 미저장
    # income_type_code: woncheon 소득구분 코드. 세무사 판정 전이라 하드코딩 금지 —
    # 항상 설정(WONCHEON_DEFAULT_INCOME_TYPE_CODE) 또는 호출 시 명시값에서만 채워짐.
    income_type_code = Column("income_type_cd", String(20), nullable=False)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
