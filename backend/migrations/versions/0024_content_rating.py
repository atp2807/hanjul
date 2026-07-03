"""콘텐츠 연령등급 — pub.book.content_rating_cd + content_rating_detail_json

플랫폼 자율등급(정부 사전승인 아님). 8기준(주제·폭력성·선정성·언어·약물·사행성·모방위험·
차별)×4단계(ALL·AGE12·AGE15·AGE18) 중 최댓값이 최종등급. detail_json = 8기준별 세부.

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "book",
        sa.Column("content_rating_cd", sa.String(10), nullable=False, server_default="ALL"),
        schema="pub",
    )
    op.add_column(
        "book",
        sa.Column("content_rating_detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="pub",
    )


def downgrade() -> None:
    op.drop_column("book", "content_rating_detail_json", schema="pub")
    op.drop_column("book", "content_rating_cd", schema="pub")
