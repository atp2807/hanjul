"""주문/정산 모델 — 스키마 `bill` (billing).

book_order = 독자의 단권 구매. settlement = 그 주문의 작가 정산 내역(1:1).
('order' 는 SQL 예약어라 테이블명은 book_order.)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "book_order"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="RESTRICT"), nullable=False)
    buyer_account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="RESTRICT"), nullable=False)
    amount_amt = Column(Numeric(15, 0), nullable=False)
    channel_cd = Column(String(20), nullable=False, default="SELF")     # SELF | EXTERNAL
    status_cd = Column(String(20), nullable=False, default="PENDING")   # PENDING | PAID | CANCELLED
    pg_provider_cd = Column(String(20))                                 # PORTONE | ...
    pg_tx_id = Column(String(255))
    # 청약철회 제한 동의 시각(전자책 제공 개시 후 철회 불가, 전자상거래법 §17⑥). NULL=미동의.
    withdrawal_consent_at = Column("withdrawal_consent_ts", DateTime(timezone=True))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    paid_at = Column("paid_ts", DateTime(timezone=True))
    refunded_at = Column("refunded_ts", DateTime(timezone=True))         # 환불 시각

    settlement = relationship("Settlement", back_populates="order", uselist=False, cascade="all, delete-orphan")


class Settlement(Base):
    __tablename__ = "settlement"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("bill.book_order.id", ondelete="CASCADE"), nullable=False, unique=True)
    channel_cd = Column(String(20), nullable=False)
    gross_amt = Column(Numeric(15, 0), nullable=False)          # 작가 몫(원천징수 전)
    platform_fee_amt = Column(Numeric(15, 0), nullable=False)
    withholding_amt = Column(Numeric(15, 0), nullable=False)
    payout_amt = Column(Numeric(15, 0), nullable=False)         # 실지급액
    # 출금 배치에 묶이면 채워짐. NULL = 미지급(출금 가능 잔액).
    payout_id = Column(UUID(as_uuid=True), ForeignKey("bill.payout.id", ondelete="SET NULL"))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)

    order = relationship("Order", back_populates="settlement")


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
