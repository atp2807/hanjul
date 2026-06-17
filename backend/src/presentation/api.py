"""API 라우터 집합 — 피처별 라우터를 여기에 include."""
from fastapi import APIRouter

from src.features.books.presentation.endpoints import router as books_router

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


router.include_router(books_router)
