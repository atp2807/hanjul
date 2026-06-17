"""계정/인증 스키마 — usr.account / usr.credential + pub.book.author_id FK

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS usr")

    op.create_table(
        "account",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True),
        sa.Column("display_name", sa.String(200)),
        sa.Column("role_cd", sa.String(20), nullable=False, server_default="READER"),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False),
        schema="usr",
    )

    op.create_table(
        "credential",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_cd", sa.String(20), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_cd", "provider_user_id", name="uq_credential_provider_user"),
        schema="usr",
    )
    op.create_index("ix_usr_credential_account_id", "credential", ["account_id"], schema="usr")

    op.create_foreign_key(
        "fk_book_author_account", "book", "account",
        ["author_id"], ["id"],
        source_schema="pub", referent_schema="usr", ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_book_author_account", "book", schema="pub", type_="foreignkey")
    op.drop_table("credential", schema="usr")
    op.drop_table("account", schema="usr")
    op.execute("DROP SCHEMA IF EXISTS usr CASCADE")
