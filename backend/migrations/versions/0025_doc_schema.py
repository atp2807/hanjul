"""한줄독(구 juldoc) 문서 도메인 — doc.document / doc.share_link

juldoc(../juldoc)의 raw SQL 마이그레이션(0001_doc.sql·0002_share.sql·0003_usr.sql)을
hanjul 컨벤션(alembic)으로 이식. juldoc 자체 usr.account는 만들지 않고 hanjul의
usr.account(id)를 그대로 참조한다. juldoc은 도메인=스키마 분리(share 별도 스키마)였지만
hanjul은 문서 도메인을 doc 스키마 하나로 묶는다(share_link도 doc.share_link로).

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS doc")

    op.create_table(
        "document",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("format_cd", sa.Text(), nullable=False, server_default=""),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.Text(), nullable=True),
        # owner_id NULL = 공용(ownerless, 무인증), 값 존재 = 잠김(juldoc 0003 점진 잠금).
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id"), nullable=True),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_ts", sa.DateTime(timezone=True), nullable=True),  # soft delete: NULL = 살아있음
        schema="doc",
    )
    # 활성 문서 조회 가속(soft delete 제외 + 최신순).
    op.create_index(
        "ix_document_active",
        "document",
        [sa.text("created_ts DESC")],
        schema="doc",
        postgresql_where=sa.text("deleted_ts IS NULL"),
    )
    # 로그인 사용자의 "내 문서" 필터 가속 (ownerless 는 인덱스에서 제외).
    op.create_index(
        "ix_document_owner",
        "document",
        ["owner_id"],
        schema="doc",
        postgresql_where=sa.text("owner_id IS NOT NULL"),
    )

    op.create_table(
        "share_link",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("doc.document.id"), nullable=False),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column("capability_cd", sa.Text(), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # 회수(revoke)는 DB 레코드가 정본: NULL 이 아니면 회수됨(재활성화 없음).
        sa.Column("revoked_ts", sa.DateTime(timezone=True), nullable=True),
        schema="doc",
    )
    # 공개 접근은 매번 토큰으로 실조회 → 토큰 인덱스로 가속(UNIQUE 가 이미 인덱스지만 명시).
    op.create_index("ix_share_link_token", "share_link", ["token"], schema="doc")
    # 문서별 발급 목록 조회 가속(최신순).
    op.create_index(
        "ix_share_link_document",
        "share_link",
        ["document_id", sa.text("created_ts DESC")],
        schema="doc",
    )


def downgrade() -> None:
    op.drop_index("ix_share_link_document", table_name="share_link", schema="doc")
    op.drop_index("ix_share_link_token", table_name="share_link", schema="doc")
    op.drop_table("share_link", schema="doc")

    op.drop_index("ix_document_owner", table_name="document", schema="doc")
    op.drop_index("ix_document_active", table_name="document", schema="doc")
    op.drop_table("document", schema="doc")

    op.execute("DROP SCHEMA IF EXISTS doc")
