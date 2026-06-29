"""신고 큐 — commu.report (책·리뷰·유저 신고 → 운영자 처리)

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reporter_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usr.account.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_type_cd", sa.String(20), nullable=False),  # BOOK | REVIEW | ACCOUNT
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column(
            "resolved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("potato.operator.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_ts", sa.DateTime(timezone=True), nullable=True),
        schema="commu",
    )
    op.create_index("ix_report_status", "report", ["status_cd"], schema="commu")
    op.create_index("ix_report_target", "report", ["target_type_cd", "target_id"], schema="commu")


def downgrade() -> None:
    op.drop_index("ix_report_target", table_name="report", schema="commu")
    op.drop_index("ix_report_status", table_name="report", schema="commu")
    op.drop_table("report", schema="commu")
