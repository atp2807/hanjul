"""한줄 ebook 백엔드 진입점 (FastAPI)."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# 모든 ORM 모델을 metadata에 등록 (create_all/Alembic 인식용)
import src.infrastructure.db.models  # noqa: F401
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from src.config.database import Base, get_engine
from src.config.settings import settings
from src.engine.publishing.sitemap import SitemapBook, build_sitemap
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.presentation.dependencies import get_catalog_service
from src.presentation.api import router as api_router
from src.shared.errors import DomainError

# sitemap.xml 정적 경로 — 공개(비로그인) 페이지만. legal slug는 web/src/legal/documents.js
# 의 DOC_ORDER 와 동기화 필요(신규 법률문서 추가 시 여기도 추가).
_SITEMAP_STATIC_PATHS = [
    "/",
    "/reviewers",
    "/pricing",
    "/legal/terms",
    "/legal/privacy",
    "/legal/refund",
    "/legal/youth",
    "/legal/copyright",
    "/legal/report",
    "/legal/cookies",
]

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


async def run_weekly_settlement_job(session, run_date) -> int:
    """매주 수요일 고정 정산 배치(lr-a0a8bda9) — 환불세이프 미지급 정산을 작가별로 묶어
    payout(REQUESTED)을 생성한다. run_date 당 최대 1회(PayoutService.run_weekly_settlement
    의 claim_settlement_run 멱등 가드). 생성된 payout 건수 반환."""
    from src.features.payouts.application.payout_service import PayoutService
    from src.features.payouts.infrastructure.payout_repo import SqlPayoutRepository

    return await PayoutService(SqlPayoutRepository(session)).run_weekly_settlement(run_date)


async def _publish_scheduler():
    """주기 작업: 예약 발행 + 신간 알림, 서평단 마감임박 알림, 매주 수요일 정산 배치."""
    from src.config.database import get_session_factory

    while True:
        await asyncio.sleep(SCHEDULER_INTERVAL_SEC)
        try:
            async with get_session_factory()() as session:
                now = datetime.now(UTC)
                n = await publish_due_and_notify(session, now)
                if n:
                    logger.info("예약발행 %d건 자동 게시", n)
                await remind_due_soon(session, now)

                now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
                if now_kst.weekday() == 2:  # 수요일(월=0)
                    settled = await run_weekly_settlement_job(session, now_kst.date())
                    if settled:
                        logger.info("주간정산 %d건 payout 생성", settled)
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


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap(svc: CatalogService = Depends(get_catalog_service)) -> Response:
    """공개 sitemap.xml — api_router(/api prefix) 밖의 루트 경로로 직접 등록.

    include_in_schema=False: SEO 인프라 엔드포인트라 API 계약(OpenAPI/스냅샷)에 넣지 않음.

    얇은 라우트: 조회는 CatalogService, XML 조립은 순수 engine(build_sitemap)에 위임.
    """
    entries = await svc.list_sitemap_entries()
    books = [SitemapBook(id=book_id, published_at=published_at) for book_id, published_at in entries]
    xml = build_sitemap(settings.FRONTEND_URL, _SITEMAP_STATIC_PATHS, books)
    return Response(content=xml, media_type="application/xml")


# 업로드 표지 정적 서빙 (/uploads/covers/...) — 작가 직접 업로드 표지
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
