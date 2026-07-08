"""API 라우터 집합 — 피처별 라우터를 여기에 include."""
from fastapi import APIRouter, Depends

from src.features.accounts.presentation.me import router as me_router
from src.features.age_verification.presentation.endpoints import (
    router as age_verification_router,
)
from src.features.age_verification.presentation.potato_endpoints import (
    router as potato_age_verification_router,
)
from src.features.auth.presentation.endpoints import router as auth_router
from src.features.billing.presentation.endpoints import payments_router
from src.features.billing.presentation.endpoints import router as billing_router
from src.features.billing.presentation.library import router as library_router
from src.features.bizverify.presentation.endpoints import router as bizverify_router
from src.features.books.presentation.content_rating_endpoints import (
    router as content_rating_router,
)
from src.features.books.presentation.endpoints import router as books_router
from src.features.books.presentation.hwp_import_endpoint import router as hwp_import_router
from src.features.books.presentation.pdf_import_endpoint import router as pdf_import_router
from src.features.campaigns.presentation.endpoints import router as campaigns_router
from src.features.catalog.presentation.endpoints import router as catalog_router
from src.features.cover.presentation.endpoints import router as cover_router
from src.features.distribution.presentation.endpoints import router as distribution_router
from src.features.doc.presentation.endpoints import router as doc_router
from src.features.manuscript.presentation.endpoints import router as manuscript_router
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
router.include_router(age_verification_router)  # 성인인증(AGE18) 신청/조회 — 인증 필수
# 운영자 영역 — IP 화이트리스트 게이트 적용 (로그인 포함 전 라우트).
_potato_guard = [Depends(require_allowed_ip)]
router.include_router(potato_router, dependencies=_potato_guard)
router.include_router(potato_moderation_router, dependencies=_potato_guard)
router.include_router(potato_reports_router, dependencies=_potato_guard)
router.include_router(potato_accounts_router, dependencies=_potato_guard)
router.include_router(potato_dashboard_router, dependencies=_potato_guard)
router.include_router(potato_payouts_router, dependencies=_potato_guard)
router.include_router(potato_age_verification_router, dependencies=_potato_guard)  # 성인인증 심사 큐
router.include_router(reports_router)  # 고객 신고 접수 — 게이트 없음
router.include_router(payouts_router)  # 작가 출금 — 인증만
router.include_router(bizverify_router)  # 사업자등록번호 진위확인 — 엔드포인트 자체 인증
router.include_router(content_rating_router)  # 콘텐츠 연령등급 — 기준 공개·작가 도구
router.include_router(hwp_import_router)  # HWP/HWPX 원고 가져오기 — 상태 없는 파싱(로그인만)
router.include_router(pdf_import_router)  # PDF 원고 가져오기 — 상태 없는 파싱(로그인만)
router.include_router(doc_router)  # 한줄독(구 juldoc) 문서·공유·미디어 — 비로그인 허용(점진 잠금)
router.include_router(manuscript_router)  # 한줄 IDE 원고 백업(일방향 push) — 인증 필수
