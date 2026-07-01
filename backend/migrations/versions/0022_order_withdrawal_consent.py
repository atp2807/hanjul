"""청약철회 제한 동의 기록 — bill.book_order.withdrawal_consent_ts

전자상거래법 §17⑥: 전자책 제공 개시 후 청약철회 제한을 적용하려면 결제 전 동의를
받아야 하며, 분쟁 시 입증책임이 사업자에게 있으므로 동의 시각을 주문에 기록한다.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "book_order",
        sa.Column("withdrawal_consent_ts", sa.DateTime(timezone=True), nullable=True),
        schema="bill",
    )


def downgrade() -> None:
    op.drop_column("book_order", "withdrawal_consent_ts", schema="bill")
