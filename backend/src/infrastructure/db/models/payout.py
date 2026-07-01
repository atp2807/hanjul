"""출금 모델 — 스키마 `bill` (payouts 피처 소유).

bank_account = 작가 출금계좌(계좌번호 암호화). payout = 미지급 정산분을 묶은 출금 배치.
정산 스냅샷 자체(book_order·settlement)는 billing 소유(models/order.py). settlement.payout_id 가
여기 payout 을 참조하지만 문자열 FK("bill.payout.id")라 순환 import 없음.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BankAccount(Base):
    """작가 출금계좌. 계좌번호는 암호화 저장(account_no_enc), 노출은 마스킹."""
    __tablename__ = "bank_account"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False)
    holder_name = Column(String(100), nullable=False)   # 예금주
    bank_cd = Column(String(20), nullable=False)         # 은행 코드/명
    account_no_enc = Column(String(255), nullable=False)  # Fernet 암호문
    account_no_masked = Column(String(50), nullable=False)  # 조회용 마스킹
    primary_yn = Column("primary_yn", Boolean, nullable=False, default=True)
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column("updated_ts", DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class Payout(Base):
    """출금 배치 — 작가의 미지급 정산분을 묶어 지급. 상태기계로 승인·지급 추적."""
    __tablename__ = "payout"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="RESTRICT"), nullable=False)
    status_cd = Column(String(20), nullable=False, default="REQUESTED")  # REQUESTED | APPROVED | PAID | REJECTED
    gross_amt = Column(Numeric(15, 0), nullable=False)         # 작가 몫 합계(원천징수 전)
    withholding_amt = Column(Numeric(15, 0), nullable=False)   # 원천징수 합계
    net_amt = Column(Numeric(15, 0), nullable=False)           # 실지급액 = gross - withholding
    # 신청 시점 계좌 스냅샷(이후 계좌 변경/삭제와 무관하게 지급 증빙)
    holder_name = Column(String(100))
    bank_cd = Column(String(20))
    account_no_masked = Column(String(50))
    requested_at = Column("requested_ts", DateTime(timezone=True), default=_now, nullable=False)
    approved_at = Column("approved_ts", DateTime(timezone=True))
    paid_at = Column("paid_ts", DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("potato.operator.id", ondelete="SET NULL"))
    memo = Column(String(500))
