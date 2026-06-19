"""서점 배포 기록 — dist.distribution

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS dist")
    op.create_table(
        "distribution",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_cd", sa.String(20), nullable=False),
        sa.Column("status_cd", sa.String(20), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        schema="dist",
    )
    op.create_index("ix_dist_distribution_book", "distribution", ["book_id"], schema="dist")


def downgrade() -> None:
    op.drop_table("distribution", schema="dist")
    op.execute("DROP SCHEMA IF EXISTS dist CASCADE")
