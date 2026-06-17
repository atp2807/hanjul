"""정본 스키마 초기 — pub.book / pub.chapter / pub.block

Revision ID: 0001
Revises:
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS pub")

    op.create_table(
        "book",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("subtitle", sa.String(500)),
        sa.Column("kind_cd", sa.String(20), nullable=False, server_default="BOOK"),
        sa.Column("language_cd", sa.String(10), nullable=False, server_default="ko"),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("cover_url", sa.String(1000)),
        sa.Column("isbn", sa.String(20)),
        sa.Column("author_id", UUID(as_uuid=True)),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False),
        schema="pub",
    )

    op.create_table(
        "chapter",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("pub.book.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("order_no", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False),
        schema="pub",
    )
    op.create_index("ix_pub_chapter_book_id", "chapter", ["book_id"], schema="pub")

    op.create_table(
        "block",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("chapter_id", UUID(as_uuid=True), sa.ForeignKey("pub.chapter.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_no", sa.Integer, nullable=False, server_default="0"),
        sa.Column("block_type_cd", sa.String(10), nullable=False, server_default="P"),
        sa.Column("html", sa.Text, nullable=False, server_default=""),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False),
        schema="pub",
    )
    op.create_index("ix_pub_block_chapter_id", "block", ["chapter_id"], schema="pub")


def downgrade() -> None:
    op.drop_table("block", schema="pub")
    op.drop_table("chapter", schema="pub")
    op.drop_table("book", schema="pub")
    op.execute("DROP SCHEMA IF EXISTS pub CASCADE")
