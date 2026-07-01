"""한줄 ebook 백엔드 진입점 (FastAPI)."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config.database import Base, get_engine
from src.config.settings import settings
from src.presentation.api import router as api_router
from src.shared.errors import DomainError

# 모든 ORM 모델을 metadata에 등록 (create_all/Alembic 인식용)
import src.infrastructure.db.models  # noqa: F401

logger = logging.getLogger("app")

SCHEDULER_INTERVAL_SEC = 30


async def publish_due_and_notify(session, now) -> int:
    """예약 시각 지난 책 자동 게시 + 게시된 책마다 작가 팔로워에게 신간 알림. 게시 건수 반환."""
    from src.features.catalog.infrastructure.catalog_repo import SqlCatalogRepository
    from src.features.notifications.application.notification_service import NotificationService
    from src.features.notifications.infrastructure.notification_repo import (
        SqlFollowRepository,
        SqlNotificationRepository,
    )

    published = await SqlCatalogRepository(session).publish_due(now)
    if not published:
        return 0
    notif = NotificationService(SqlFollowRepository(session), SqlNotificationRepository(session))
    for book_id, author_id, title in published:
        try:
            await notif.notify_new_book(book_id, author_id, title)
        except Exception:
            logger.exception("예약발행 신간 알림 실패 (book=%s) — 게시는 정상", book_id)
    return len(published)


async def remind_due_soon(session, now, within_days: int = 2) -> int:
    """서평단 리뷰 마감 임박(기한 within_days 내) 리뷰어에게 ⏰ 알림. (리뷰어,책)당 1회(멱등). 보낸 수 반환."""
    from src.features.campaigns.infrastructure.campaign_repo import SqlCampaignRepository
    from src.features.notifications.application.notification_service import NotificationService
    from src.features.notifications.infrastructure.notification_repo import (
        SqlFollowRepository,
        SqlNotificationRepository,
    )

    due = await SqlCampaignRepository(session).due_soon(now, within_days)
    if not due:
        return 0
    notif = NotificationService(SqlFollowRepository(session), SqlNotificationRepository(session))
    for reviewer_id, book_id, title in due:
        try:
            await notif.notify_due_soon(reviewer_id, book_id, title)
        except Exception:
            logger.exception("마감임박 알림 실패 (reviewer=%s book=%s)", reviewer_id, book_id)
    return len(due)


async def _publish_scheduler():
    """주기 작업: 예약 발행 + 신간 알림, 서평단 마감임박 알림."""
    from src.config.database import get_session_factory

    while True:
        await asyncio.sleep(SCHEDULER_INTERVAL_SEC)
        try:
            async with get_session_factory()() as session:
                now = datetime.now(timezone.utc)
                n = await publish_due_and_notify(session, now)
                if n:
                    logger.info("예약발행 %d건 자동 게시", n)
                await remind_due_soon(session, now)
        except Exception:
            logger.exception("스케줄러 오류")


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
    allow_origins=settings.cors_origin_list,  # dev=localhost, 운영=CORS_ORIGINS/FRONTEND_URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(DomainError)
async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """도메인 예외 → HTTP. 표현층의 수동 try/except 매핑을 대체한다."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(api_router)

# 업로드 표지 정적 서빙 (/uploads/covers/...) — 작가 직접 업로드 표지
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
