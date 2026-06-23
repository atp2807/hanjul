"""무료 미리보기 분량 — pub.book.preview_block_cnt

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "book",
        sa.Column("preview_block_cnt", sa.Integer(), nullable=False, server_default="3"),
        schema="pub",
    )


def downgrade() -> None:
    op.drop_column("book", "preview_block_cnt", schema="pub")
