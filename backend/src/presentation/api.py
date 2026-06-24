"""API 라우터 집합 — 피처별 라우터를 여기에 include."""
from fastapi import APIRouter

from src.features.auth.presentation.endpoints import router as auth_router
from src.features.auth.presentation.me import router as me_router
from src.features.books.presentation.endpoints import router as books_router
from src.features.billing.presentation.endpoints import payments_router
from src.features.billing.presentation.endpoints import router as billing_router
from src.features.billing.presentation.library import router as library_router
from src.features.catalog.presentation.endpoints import router as catalog_router
from src.features.cover.presentation.endpoints import router as cover_router
from src.features.distribution.presentation.endpoints import router as distribution_router
from src.features.notifications.presentation.endpoints import router as notifications_router
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
