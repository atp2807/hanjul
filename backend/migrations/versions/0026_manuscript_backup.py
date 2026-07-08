"""ms 스키마 — 데스크탑 원고 백업(append-only 리비전 로그). 한줄 IDE P1 슬라이스7.

ms.manuscript_book: 데스크탑 book.sync_key(UUID) ↔ 서버 엔티티를 잇는 백업 전용 테이블
(pub.book과 무관 — 발행은 books 피처, 이건 데스크탑 백업 전용). usr.account 소유(FK),
sync_key UNIQUE — 재설치/재발행에도 같은 책으로 인식.
ms.manuscript_revision: append-only(챕터별 저장 이력) — content_hash 로 dedup, 챕터당
50개 초과분은 오래된 것부터 prune(애플리케이션 레이어에서 수행, 마이그레이션은 스키마만).

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ms")

    op.create_table(
        "manuscript_book",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("usr.account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_key", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="ms",
    )
    # 계정별 백업 책 목록 조회 가속(P2 동기화 토대 — 현재는 sync_key 단건 조회뿐이지만 미리).
    op.create_index("ix_manuscript_book_account", "manuscript_book", ["account_id"], schema="ms")

    op.create_table(
        "manuscript_revision",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("book_id", UUID(as_uuid=True), sa.ForeignKey("ms.manuscript_book.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_key", sa.Text(), nullable=False),
        sa.Column("chapter_title", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="ms",
    )
    # 챕터별 최신 리비전 조회/prune 가속 — book_id+chapter_key 로 좁힌 뒤 최신순.
    op.create_index(
        "ix_manuscript_revision_book_chapter",
        "manuscript_revision",
        ["book_id", "chapter_key", sa.text("created_ts DESC")],
        schema="ms",
    )


def downgrade() -> None:
    op.drop_index("ix_manuscript_revision_book_chapter", table_name="manuscript_revision", schema="ms")
    op.drop_table("manuscript_revision", schema="ms")

    op.drop_index("ix_manuscript_book_account", table_name="manuscript_book", schema="ms")
    op.drop_table("manuscript_book", schema="ms")

    op.execute("DROP SCHEMA IF EXISTS ms")
