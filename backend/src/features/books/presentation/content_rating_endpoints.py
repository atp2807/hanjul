"""콘텐츠 연령등급 API — 기준 조회(공개) + 자동분류 추천 + 작가 오버라이드.

소유권은 catalog의 require_book_owner 재사용(cover/distribution과 동일 패턴, 없는 책 404·
타인 403). RuntimeError(키 미설정·외부실패)는 반드시 503으로 잡는다 — 놓치면 500이 새 나감.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.books.application.content_rating_service import ContentRatingService
from src.features.books.domain.content_rating import load_criteria
from src.features.books.presentation.dependencies import get_content_rating_service
from src.features.books.presentation.schemas import (
    ContentRatingResponse,
    SetContentRatingRequest,
)
from src.features.catalog.presentation.endpoints import require_book_owner

router = APIRouter(tags=["content-rating"])


@router.get("/content-rating/criteria")
async def get_criteria() -> dict:
    """등급 기준 원문(8기준×4단계 가이드) — 인증 불필요. 프론트 select 라벨/헬퍼용."""
    return load_criteria()


@router.post("/books/{book_id}/content-rating/suggest", response_model=ContentRatingResponse)
async def suggest_rating(
    book_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: ContentRatingService = Depends(get_content_rating_service),
    _owner: None = Depends(require_book_owner),  # 소유 작가만 (없는 책 404 / 타인 403)
) -> ContentRatingResponse:
    """본문 기반 AI 자동분류 추천 → 8기준 + 최종등급 저장·반환."""
    try:
        rating, detail = await svc.suggest_rating(book_id, principal.id)
    except RuntimeError:
        raise HTTPException(503, "등급 자동분류가 지금은 불가해요. 잠시 후 다시 시도해 주세요.")
    return ContentRatingResponse(content_rating=rating, content_rating_detail=detail)


@router.put("/books/{book_id}/content-rating", response_model=ContentRatingResponse)
async def set_rating(
    book_id: UUID,
    body: SetContentRatingRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: ContentRatingService = Depends(get_content_rating_service),
    _owner: None = Depends(require_book_owner),  # 소유 작가만
) -> ContentRatingResponse:
    """작가 오버라이드(일부/전체) → 병합·최종등급 재계산·저장. 잘못된 값 422(도메인 예외)."""
    rating, detail = await svc.set_rating(book_id, principal.id, body.detail)
    return ContentRatingResponse(content_rating=rating, content_rating_detail=detail)
