"""작가 팔로우 + 인앱 알림함 — commu.follow / commu.notification

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS commu")
    # 독자 → 작가 팔로우 (한 쌍 유일)
    op.create_table(
        "follow",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("follower_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("follower_id", "author_id", name="uq_follow_pair"),
        schema="commu",
    )
    op.create_index("ix_commu_follow_author", "follow", ["author_id"], schema="commu")
    # 인앱 알림 (수신자별 · (수신자,책,종류) 유일 → 재발행 멱등)
    op.create_table(
        "notification",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("recipient_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind_cd", sa.String(20), nullable=False),  # NEW_BOOK
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("pub.book.id", ondelete="CASCADE")),
        sa.Column("title", sa.Text),
        sa.Column("read_yn", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("recipient_id", "book_id", "kind_cd", name="uq_notification_recipient_book_kind"),
        schema="commu",
    )
    op.create_index("ix_commu_notification_recipient", "notification", ["recipient_id"], schema="commu")


def downgrade() -> None:
    op.drop_table("notification", schema="commu")
    op.drop_table("follow", schema="commu")
