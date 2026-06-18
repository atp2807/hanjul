"""한줄 ebook 백엔드 진입점 (FastAPI)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import Base, get_engine
from src.config.settings import settings
from src.presentation.api import router as api_router

# 모든 ORM 모델을 metadata에 등록 (create_all/Alembic 인식용)
import src.infrastructure.db.models  # noqa: F401

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DEBUG 한정 — 개발 편의를 위한 자동 테이블 생성. 운영은 Alembic 마이그레이션 사용.
    if settings.DEBUG:
        async with get_engine().begin() as conn:
            await conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS pub")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DEV] pub 스키마 + 테이블 자동 생성 완료")
    yield


app = FastAPI(title="한줄 ebook API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:35173"],  # Vite dev server (웰노운 포트 회피)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
