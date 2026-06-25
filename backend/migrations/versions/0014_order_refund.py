"""주문 환불 — bill.book_order.refunded_ts (status_cd REFUNDED 보조)

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book_order", sa.Column("refunded_ts", sa.DateTime(timezone=True)), schema="bill")


def downgrade() -> None:
    op.drop_column("book_order", "refunded_ts", schema="bill")
