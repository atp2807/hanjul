"""리뷰 출처 — commu.review.source_cd (PURCHASE | REVIEW_COPY, 서평단 배지 근거)

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review",
        sa.Column("source_cd", sa.String(20), nullable=False, server_default="PURCHASE"),
        schema="commu",
    )


def downgrade() -> None:
    op.drop_column("review", "source_cd", schema="commu")
