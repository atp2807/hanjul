"""서평단 자격회수를 commu로 이전 — usr.account.review_blocked_ts → commu.reviewer_block

서평단(commu) 개념이 usr.account에 얹혀 있던 오염 정리. 기존 데이터 보존 이전.

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviewer_block",
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usr.account.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("blocked_until_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="commu",
    )
    # 기존 차단 데이터 이전 (NULL=정상은 제외)
    op.execute(
        "INSERT INTO commu.reviewer_block (account_id, blocked_until_ts, created_ts, updated_ts) "
        "SELECT id, review_blocked_ts, now(), now() FROM usr.account WHERE review_blocked_ts IS NOT NULL"
    )
    op.drop_column("account", "review_blocked_ts", schema="usr")


def downgrade() -> None:
    op.add_column(
        "account",
        sa.Column("review_blocked_ts", sa.DateTime(timezone=True), nullable=True),
        schema="usr",
    )
    op.execute(
        "UPDATE usr.account a SET review_blocked_ts = b.blocked_until_ts "
        "FROM commu.reviewer_block b WHERE a.id = b.account_id"
    )
    op.drop_table("reviewer_block", schema="commu")
