"""한줄 ebook 백엔드 진입점 (FastAPI)."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import Base, get_engine
from src.config.settings import settings
from src.presentation.api import router as api_router

# 모든 ORM 모델을 metadata에 등록 (create_all/Alembic 인식용)
import src.infrastructure.db.models  # noqa: F401

logger = logging.getLogger("app")

SCHEDULER_INTERVAL_SEC = 30


async def _publish_scheduler():
    """예약 발행: 주기적으로 예약 시각 지난 책을 자동 게시."""
    from src.config.database import get_session_factory
    from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository

    while True:
        await asyncio.sleep(SCHEDULER_INTERVAL_SEC)
        try:
            async with get_session_factory()() as session:
                n = await SqlCatalogRepository(session).publish_due(datetime.now(timezone.utc))
                if n:
                    logger.info("예약발행 %d건 자동 게시", n)
        except Exception:
            logger.exception("예약발행 스케줄러 오류")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DEBUG 한정 — 개발 편의를 위한 자동 테이블 생성. 운영은 Alembic 마이그레이션 사용.
    if settings.DEBUG:
        async with get_engine().begin() as conn:
            await conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS pub")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DEV] pub 스키마 + 테이블 자동 생성 완료")
    scheduler = asyncio.create_task(_publish_scheduler())
    try:
        yield
    finally:
        scheduler.cancel()


app = FastAPI(title="한줄 ebook API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:35173"],  # Vite dev server (웰노운 포트 회피)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
