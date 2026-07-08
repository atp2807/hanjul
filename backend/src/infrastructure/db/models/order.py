"""주문/정산 모델 — 스키마 `bill` (billing 피처 소유).

book_order = 독자의 단권 구매. settlement = 그 주문의 작가 정산 내역(1:1).
('order' 는 SQL 예약어라 테이블명은 book_order.)
출금 관련(bank_account·payout)은 payouts 피처 소유 → models/payout.py.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Order(Base):
    __tablename__ = "book_order"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("pub.book.id", ondelete="RESTRICT"), nullable=False)
    buyer_account_id = Column(UUID(as_uuid=True), ForeignKey("usr.account.id", ondelete="RESTRICT"), nullable=False)
    amount_amt = Column(Numeric(15, 0), nullable=False)
    channel = Column("channel_cd", String(20), nullable=False, default="SELF")   # SELF | EXTERNAL
    status = Column("status_cd", String(20), nullable=False, default="PENDING")  # PENDING | PAID | CANCELLED
    pg_provider = Column("pg_provider_cd", String(20))                                 # PORTONE | ...
    pg_tx_id = Column(String(255))
    # 청약철회 제한 동의 시각(전자책 제공 개시 후 철회 불가, 전자상거래법 §17⑥). NULL=미동의.
    withdrawal_consent_at = Column("withdrawal_consent_ts", DateTime(timezone=True))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    paid_at = Column("paid_ts", DateTime(timezone=True))
    refunded_at = Column("refunded_ts", DateTime(timezone=True))         # 환불 시각
    # 전자책 제공 개시(첫 전체열람/다운로드) 시각 — 환불세이프(청약철회 제한) 판정용. NULL=미개시.
    delivered_at = Column("delivered_ts", DateTime(timezone=True))

    settlement = relationship("Settlement", back_populates="order", uselist=False, cascade="all, delete-orphan")


class Settlement(Base):
    __tablename__ = "settlement"
    __table_args__ = {"schema": "bill"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("bill.book_order.id", ondelete="CASCADE"), nullable=False, unique=True)
    channel = Column("channel_cd", String(20), nullable=False)
    gross_amt = Column(Numeric(15, 0), nullable=False)          # 작가 몫(원천징수 전)
    platform_fee_amt = Column(Numeric(15, 0), nullable=False)
    withholding_amt = Column(Numeric(15, 0), nullable=False)
    payout_amt = Column(Numeric(15, 0), nullable=False)         # 실지급액
    # 출금 배치에 묶이면 채워짐. NULL = 미지급(출금 가능 잔액).
    payout_id = Column(UUID(as_uuid=True), ForeignKey("bill.payout.id", ondelete="SET NULL"))
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)

    order = relationship("Order", back_populates="settlement")
