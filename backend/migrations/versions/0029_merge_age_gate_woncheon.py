"""merge — 0027(연령게이트)·0028(원천징수 커넥터) 병렬 브랜치 병합.

같은 세션에서 두 트랙(연령게이트·woncheon 커넥터)이 동시에 0026에서 분기해 head가
2개(0027/0028)가 됐다 — 순수 병합 지점, 스키마 변경 없음.

Revision ID: 0029
Revises: 0027, 0028
Create Date: 2026-07-08
"""
from __future__ import annotations

revision = "0029"
down_revision = ("0027", "0028")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
