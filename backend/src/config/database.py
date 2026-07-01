"""DB 엔진 + 세션 (async SQLAlchemy 2.0).

haedream 패턴을 따라 엔진은 **지연 생성(lazy)** — 모듈 import 시점에 DB 드라이버를
당기지 않으므로, 모델/메타데이터는 드라이버 없이도 빌드·검증할 수 있다.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 — 요청 단위 세션 (고객 DB 유저)."""
    async with get_session_factory()() as session:
        yield session


# ── 운영자(potato) 전용 세션 — potato.operator/audit_log 접근 ──────────
_potato_engine: AsyncEngine | None = None
_potato_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_potato_session_factory() -> async_sessionmaker[AsyncSession]:
    """POTATO_DATABASE_URL 있으면 별도(저권한) 엔진, 없으면 메인 재사용(dev/test)."""
    if not settings.POTATO_DATABASE_URL:
        return get_session_factory()
    global _potato_engine, _potato_session_factory
    if _potato_session_factory is None:
        _potato_engine = create_async_engine(
            settings.POTATO_DATABASE_URL,
            pool_size=2,
            max_overflow=3,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        _potato_session_factory = async_sessionmaker(
            _potato_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _potato_session_factory


async def get_potato_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 — 운영자 전용 세션 (potato 스키마 접근)."""
    async with get_potato_session_factory()() as session:
        yield session
