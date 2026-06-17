"""API 라우터 집합 — 피처별 라우터를 여기에 include."""
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# 피처 라우터 등록 위치 (예: router.include_router(books_router))
