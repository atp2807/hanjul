"""통합 테스트 공용 — 실 SQLAlchemy 엔진(in-memory SQLite)으로 ORM/레포를 검증.

운영은 PostgreSQL 이지만, 이식 가능한 스모크를 위해 SQLite 사용:
- schema_translate_map={'pub': None} → pub 스키마를 SQLite 에서 무시 (모델 변경 0)
- StaticPool + 단일 연결 → in-memory DB 를 모든 세션이 공유
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.config.database import Base
import src.infrastructure.db.models  # noqa: F401  (메타데이터 등록)


@pytest_asyncio.fixture
async def sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": {"pub": None, "usr": None, "bill": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()
