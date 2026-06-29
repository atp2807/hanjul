"""운영자 분리 영역 — potato.operator + potato.audit_log

고객(usr.account)과 완전 분리된 운영자 인증 영역. 별도 스키마.

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS potato")
    op.create_table(
        "operator",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("role_cd", sa.String(20), nullable=False, server_default="OPERATOR"),
        sa.Column("active_yn", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_operator_email"),
        schema="potato",
    )
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_id",
            UUID(as_uuid=True),
            sa.ForeignKey("potato.operator.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("detail", JSONB(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="potato",
    )
    op.create_index("ix_audit_log_operator", "audit_log", ["operator_id"], schema="potato")
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"], schema="potato")


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity", table_name="audit_log", schema="potato")
    op.drop_index("ix_audit_log_operator", table_name="audit_log", schema="potato")
    op.drop_table("audit_log", schema="potato")
    op.drop_table("operator", schema="potato")
    op.execute("DROP SCHEMA IF EXISTS potato")
