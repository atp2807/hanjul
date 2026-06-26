"""서평단 자격회수 — usr.account.review_blocked_ts (미작성 누적 시 신청 제한)

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이 시각까지 서평단 신청 제한(자격회수). NULL = 정상.
    op.add_column(
        "account",
        sa.Column("review_blocked_ts", sa.DateTime(timezone=True), nullable=True),
        schema="usr",
    )


def downgrade() -> None:
    op.drop_column("account", "review_blocked_ts", schema="usr")
