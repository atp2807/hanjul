"""서평단 캠페인 — commu.review_campaign / commu.review_application

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS commu")
    op.create_table(
        "review_campaign",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slots", sa.Integer, nullable=False),          # 증정본 수
        sa.Column("filled", sa.Integer, nullable=False, server_default="0"),  # 배정된 수
        sa.Column("review_days", sa.Integer, nullable=False, server_default="7"),  # 배정 후 리뷰 기한(일)
        sa.Column("min_chars", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="OPEN"),  # OPEN | CLOSED
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        schema="commu",
    )
    op.create_index("ix_commu_campaign_status", "review_campaign", ["status_cd"], schema="commu")
    op.create_table(
        "review_application",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("commu.review_campaign.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="PENDING"),  # PENDING | ASSIGNED
        sa.Column("assigned_ts", sa.DateTime(timezone=True)),
        sa.Column("deadline_ts", sa.DateTime(timezone=True)),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("campaign_id", "applicant_id", name="uq_application_campaign_applicant"),
        schema="commu",
    )
    op.create_index("ix_commu_application_campaign", "review_application", ["campaign_id"], schema="commu")
    op.create_index("ix_commu_application_applicant", "review_application", ["applicant_id"], schema="commu")


def downgrade() -> None:
    op.drop_table("review_application", schema="commu")
    op.drop_table("review_campaign", schema="commu")
