"""예약발행 — pub.book.scheduled_publish_ts

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book", sa.Column("scheduled_publish_ts", sa.DateTime(timezone=True)), schema="pub")
    op.create_index(
        "ix_pub_book_scheduled",
        "book",
        ["scheduled_publish_ts"],
        schema="pub",
        postgresql_where=sa.text("scheduled_publish_ts IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_pub_book_scheduled", "book", schema="pub")
    op.drop_column("book", "scheduled_publish_ts", schema="pub")
