"""API 라우터 집합 — 피처별 라우터를 여기에 include."""
from fastapi import APIRouter, Depends

from src.features.accounts.presentation.me import router as me_router
from src.features.auth.presentation.endpoints import router as auth_router
from src.features.billing.presentation.endpoints import payments_router
from src.features.billing.presentation.endpoints import router as billing_router
from src.features.billing.presentation.library import router as library_router
from src.features.books.presentation.endpoints import router as books_router
from src.features.campaigns.presentation.endpoints import router as campaigns_router
from src.features.catalog.presentation.endpoints import router as catalog_router
from src.features.cover.presentation.endpoints import router as cover_router
from src.features.distribution.presentation.endpoints import router as distribution_router
from src.features.notifications.presentation.endpoints import router as notifications_router
from src.features.payouts.presentation.endpoints import router as payouts_router
from src.features.potato.presentation.accounts import router as potato_accounts_router
from src.features.potato.presentation.dashboard import router as potato_dashboard_router
from src.features.potato.presentation.dependencies import require_allowed_ip
from src.features.potato.presentation.endpoints import router as potato_router
from src.features.potato.presentation.moderation import router as potato_moderation_router
from src.features.potato.presentation.payouts import router as potato_payouts_router
from src.features.potato.presentation.reports import router as potato_reports_router
from src.features.reports.presentation.endpoints import router as reports_router
from src.features.reviews.presentation.endpoints import router as reviews_router

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


router.include_router(books_router)
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(catalog_router)
router.include_router(billing_router)
router.include_router(payments_router)
router.include_router(library_router)
router.include_router(cover_router)
router.include_router(distribution_router)
router.include_router(reviews_router)
router.include_router(notifications_router)
router.include_router(campaigns_router)
# 운영자 영역 — IP 화이트리스트 게이트 적용 (로그인 포함 전 라우트).
_potato_guard = [Depends(require_allowed_ip)]
router.include_router(potato_router, dependencies=_potato_guard)
router.include_router(potato_moderation_router, dependencies=_potato_guard)
router.include_router(potato_reports_router, dependencies=_potato_guard)
router.include_router(potato_accounts_router, dependencies=_potato_guard)
router.include_router(potato_dashboard_router, dependencies=_potato_guard)
router.include_router(potato_payouts_router, dependencies=_potato_guard)
router.include_router(reports_router)  # 고객 신고 접수 — 게이트 없음
router.include_router(payouts_router)  # 작가 출금 — 인증만
