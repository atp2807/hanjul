"""책 출판 필드 — pub.book.price_amt / published_ts

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book", sa.Column("price_amt", sa.Numeric(15, 0)), schema="pub")
    op.add_column("book", sa.Column("published_ts", sa.DateTime(timezone=True)), schema="pub")
    op.create_index("ix_pub_book_status", "book", ["status_cd"], schema="pub")


def downgrade() -> None:
    op.drop_index("ix_pub_book_status", "book", schema="pub")
    op.drop_column("book", "published_ts", schema="pub")
    op.drop_column("book", "price_amt", schema="pub")
