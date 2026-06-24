"""기간 할인 — pub.book.discount_amt / discount_until_ts

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book", sa.Column("discount_amt", sa.Numeric(15, 0), nullable=True), schema="pub")
    op.add_column("book", sa.Column("discount_until_ts", sa.DateTime(timezone=True), nullable=True), schema="pub")


def downgrade() -> None:
    op.drop_column("book", "discount_until_ts", schema="pub")
    op.drop_column("book", "discount_amt", schema="pub")
