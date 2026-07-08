"""연령 게이트(알라딘식 v1) — usr.account.verified_tier_cd + usr.age_verification_request

설계 정본 LinkLore dc-daeb0d3d. 등급 분류(pub.book.content_rating_cd, 0024)는 이미 완성 —
여기는 계정 인증등급 컬럼 1개 + 인증요청 상태기계 테이블 1개만 추가한다.

인증 v1 = 수동(신분증 사진 업로드 → potato 운영자 승인/거부). 심사 완료 즉시 원본 이미지
삭제 방침이라 id_photo_key는 심사 후 NULL로 되돌아간다(애플리케이션 레이어가 처리).

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "account",
        sa.Column("verified_tier_cd", sa.String(10), nullable=False, server_default="ALL"),
        schema="usr",
    )

    op.create_table(
        "age_verification_request",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        # 신분증 사진 저장 키(비공개 스토리지) — 심사 완료(승인/거부) 즉시 NULL로 되돌리고 원본 삭제.
        sa.Column("id_photo_key", sa.String(255), nullable=True),
        sa.Column("status_cd", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("potato.operator.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="usr",
    )
    op.create_index("ix_age_verification_request_account", "age_verification_request", ["account_id"], schema="usr")
    op.create_index("ix_age_verification_request_status", "age_verification_request", ["status_cd"], schema="usr")


def downgrade() -> None:
    op.drop_index("ix_age_verification_request_status", table_name="age_verification_request", schema="usr")
    op.drop_index("ix_age_verification_request_account", table_name="age_verification_request", schema="usr")
    op.drop_table("age_verification_request", schema="usr")

    op.drop_column("account", "verified_tier_cd", schema="usr")
