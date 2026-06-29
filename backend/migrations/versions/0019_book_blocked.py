"""운영자 takedown — pub.book.blocked_ts (강제 비공개, 작가 라이프사이클과 직교)

NULL = 정상. 값 = 운영자가 내린 시각. 작가가 재출판(status)해도 풀리지 않음.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "book",
        sa.Column("blocked_ts", sa.DateTime(timezone=True), nullable=True),
        schema="pub",
    )


def downgrade() -> None:
    op.drop_column("book", "blocked_ts", schema="pub")
