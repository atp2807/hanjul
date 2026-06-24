"""작가 소개 — usr.account.bio

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("account", sa.Column("bio", sa.Text(), nullable=True), schema="usr")


def downgrade() -> None:
    op.drop_column("account", "bio", schema="usr")
