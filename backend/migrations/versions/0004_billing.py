"""결제/정산 스키마 — bill.book_order / bill.settlement

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS bill")

    op.create_table(
        "book_order",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("pub.book.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("buyer_account_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("channel_cd", sa.String(20), nullable=False, server_default="SELF"),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("pg_provider_cd", sa.String(20)),
        sa.Column("pg_tx_id", sa.String(255)),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_ts", sa.DateTime(timezone=True)),
        schema="bill",
    )
    op.create_index("ix_bill_order_buyer", "book_order", ["buyer_account_id"], schema="bill")
    op.create_index("ix_bill_order_book", "book_order", ["book_id"], schema="bill")

    op.create_table(
        "settlement",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("bill.book_order.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("channel_cd", sa.String(20), nullable=False),
        sa.Column("gross_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("platform_fee_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("withholding_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("payout_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        schema="bill",
    )


def downgrade() -> None:
    op.drop_table("settlement", schema="bill")
    op.drop_table("book_order", schema="bill")
    op.execute("DROP SCHEMA IF EXISTS bill CASCADE")
