"""리뷰 수정시각 — commu.review.updated_ts ('수정됨' 표시)

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 재작성 시 갱신. 기존 행은 NULL(= 수정 이력 없음).
    op.add_column("review", sa.Column("updated_ts", sa.DateTime(timezone=True)), schema="commu")


def downgrade() -> None:
    op.drop_column("review", "updated_ts", schema="commu")
