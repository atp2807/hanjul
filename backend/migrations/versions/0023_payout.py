"""작가 출금 인프라 — bill.bank_account + bill.payout + settlement.payout_id

계좌등록(암호화) → 미지급 정산분 집계 → 출금신청(payout) → 운영자 승인·지급.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_account",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("holder_name", sa.String(100), nullable=False),
        sa.Column("bank_cd", sa.String(20), nullable=False),
        sa.Column("account_no_enc", sa.String(255), nullable=False),
        sa.Column("account_no_masked", sa.String(50), nullable=False),
        sa.Column("primary_yn", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="bill",
    )
    op.create_index("ix_bank_account_owner", "bank_account", ["account_id"], schema="bill")

    op.create_table(
        "payout",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="REQUESTED"),
        sa.Column("gross_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("withholding_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("net_amt", sa.Numeric(15, 0), nullable=False),
        sa.Column("holder_name", sa.String(100), nullable=True),
        sa.Column("bank_cd", sa.String(20), nullable=True),
        sa.Column("account_no_masked", sa.String(50), nullable=True),
        sa.Column("requested_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("potato.operator.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memo", sa.String(500), nullable=True),
        schema="bill",
    )
    op.create_index("ix_payout_author", "payout", ["author_id"], schema="bill")
    op.create_index("ix_payout_status", "payout", ["status_cd"], schema="bill")

    op.add_column(
        "settlement",
        sa.Column("payout_id", UUID(as_uuid=True), sa.ForeignKey("bill.payout.id", ondelete="SET NULL"), nullable=True),
        schema="bill",
    )
    op.create_index("ix_settlement_payout", "settlement", ["payout_id"], schema="bill")


def downgrade() -> None:
    op.drop_index("ix_settlement_payout", table_name="settlement", schema="bill")
    op.drop_column("settlement", "payout_id", schema="bill")
    op.drop_index("ix_payout_status", table_name="payout", schema="bill")
    op.drop_index("ix_payout_author", table_name="payout", schema="bill")
    op.drop_table("payout", schema="bill")
    op.drop_index("ix_bank_account_owner", table_name="bank_account", schema="bill")
    op.drop_table("bank_account", schema="bill")
