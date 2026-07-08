"""raw SQL 마이그레이션 러너 (alembic 대체, 2026-07-08 — no-alembic-rule.md 참조).

Usage:
    .venv312/bin/python migrate.py              # 대기 중인 마이그레이션 전부 적용
    .venv312/bin/python migrate.py --reset      # 전 스키마 DROP 후 처음부터 재적용
    .venv312/bin/python migrate.py 001          # 파일명이 주어진 번호로 시작하는 것만
"""

import asyncio
import glob
import os
import sys

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://daviy@127.0.0.1:5432/hanjul_ebook",
).replace("postgresql+asyncpg://", "postgresql://")

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

MIGRATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.migration_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(200) NOT NULL UNIQUE,
    applied_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

RESET_SQL = """
DROP SCHEMA IF EXISTS bill CASCADE;
DROP SCHEMA IF EXISTS commu CASCADE;
DROP SCHEMA IF EXISTS dist CASCADE;
DROP SCHEMA IF EXISTS doc CASCADE;
DROP SCHEMA IF EXISTS ms CASCADE;
DROP SCHEMA IF EXISTS potato CASCADE;
DROP SCHEMA IF EXISTS pub CASCADE;
DROP SCHEMA IF EXISTS usr CASCADE;
DROP TABLE IF EXISTS public.migration_history;
DROP TABLE IF EXISTS public.alembic_version;
"""


async def run_migrations(reset: bool = False, only: list[str] | None = None) -> None:
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        if reset:
            print("Resetting all schemas...")
            await conn.execute(RESET_SQL)
            print("Done.\n")

        await conn.execute(MIGRATION_TABLE_SQL)

        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM public.migration_history")
        }

        sql_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))

        if only:
            sql_files = [
                f for f in sql_files
                if any(os.path.basename(f).startswith(n) for n in only)
            ]
            if not sql_files:
                print(f"No migrations match: {only}")
                return

        pending = [
            (os.path.basename(f), f) for f in sql_files
            if os.path.basename(f) not in applied
        ]

        if not pending:
            print("No pending migrations.")
            return

        for filename, filepath in pending:
            print(f"Applying {filename}...")
            with open(filepath) as f:  # noqa: ASYNC230 (일회성 CLI, 이벤트루프 경합 없음)
                sql = f.read()
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO public.migration_history (filename) VALUES ($1)", filename
            )
            print("  OK")

        print(f"\n{len(pending)} migration(s) applied.")

    finally:
        await conn.close()


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    asyncio.run(run_migrations(reset=reset, only=only or None))
