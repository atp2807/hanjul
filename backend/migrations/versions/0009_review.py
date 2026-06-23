"""리뷰·평점 — commu.review

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS commu")
    op.create_table(
        "review",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("body", sa.Text),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("book_id", "account_id", name="uq_review_book_account"),
        schema="commu",
    )
    op.create_index("ix_commu_review_book", "review", ["book_id"], schema="commu")


def downgrade() -> None:
    op.drop_table("review", schema="commu")
    op.execute("DROP SCHEMA IF EXISTS commu CASCADE")
