"""주문/정산 모델 — 스키마 `bill` (billing).

book_order = 독자의 단권 구매. settlement = 그 주문의 작가 정산 내역(1:1).
('order' 는 SQL 예약어라 테이블명은 book_order.)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
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
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)
    paid_at = Column("paid_ts", DateTime(timezone=True))

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
    created_at = Column("created_ts", DateTime(timezone=True), default=_now, nullable=False)

    order = relationship("Order", back_populates="settlement")
