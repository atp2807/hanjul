"""woncheon 원천징수 신고 커넥터 — payout.woncheon_reported_ts + bill.withholding_subject.

스켈레톤(lr-ac61f505): hanjul_woncheon(B2B 세무 자동화 API)에 payout PAID 이벤트를
전달하는 커넥터용 테이블만. 실 woncheon 테넌트 미등록(api_key 없음)·소득구분(3.3%/8%)
세무사 미판정 상태라 이 마이그레이션은 순수 스키마 골격이고 실제 신고 로직은
포트+어댑터+Fake로 완결(네트워크 호출 없음).

주민번호는 지급 시점·원천징수 대상 작가만 최소수집(계좌등록=bill.bank_account 과 별개
테이블 — 과잉수집 금지), Fernet 암호화(bill.bank_account.account_no_enc 와 같은 키
관리 패턴 재사용).

Revision ID: 0028
Revises: 0026
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0028"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payout",
        sa.Column("woncheon_reported_ts", sa.DateTime(timezone=True), nullable=True),
        schema="bill",
    )

    op.create_table(
        "withholding_subject",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("payout_id", UUID(as_uuid=True), sa.ForeignKey("bill.payout.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resident_no_enc", sa.String(255), nullable=False),
        sa.Column("income_type_cd", sa.String(20), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="bill",
    )
    op.create_index(
        "ix_withholding_subject_payout", "withholding_subject", ["payout_id"], unique=True, schema="bill"
    )


def downgrade() -> None:
    op.drop_index("ix_withholding_subject_payout", table_name="withholding_subject", schema="bill")
    op.drop_table("withholding_subject", schema="bill")
    op.drop_column("payout", "woncheon_reported_ts", schema="bill")
