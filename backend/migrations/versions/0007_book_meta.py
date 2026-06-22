"""책 메타 — pub.book.description / category_cd

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book", sa.Column("description", sa.Text(), nullable=True), schema="pub")
    op.add_column("book", sa.Column("category_cd", sa.String(40), nullable=True), schema="pub")


def downgrade() -> None:
    op.drop_column("book", "category_cd", schema="pub")
    op.drop_column("book", "description", schema="pub")
