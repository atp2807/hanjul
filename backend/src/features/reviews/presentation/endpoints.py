"""reviews API — 평점·리뷰 작성/조회."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.reviews.application.review_service import ReviewService
from src.features.reviews.infrastructure.review_repo import SqlReviewRepository
from src.features.reviews.presentation.schemas import (
    AddReviewRequest,
    ReviewItem,
    ReviewListResponse,
)

router = APIRouter(tags=["reviews"])


def _svc(session: AsyncSession) -> ReviewService:
    return ReviewService(SqlReviewRepository(session))


@router.post("/books/{book_id}/reviews", status_code=201)
async def add_review(
    book_id: UUID,
    body: AddReviewRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """리뷰·평점 작성(로그인 필요). (책,계정)당 한 건 — 다시 쓰면 갱신."""
    try:
        await _svc(session).add(book_id, principal.id, body.rating, body.body)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"ok": True}


@router.get("/books/{book_id}/reviews", response_model=ReviewListResponse)
async def list_reviews(
    book_id: UUID, session: AsyncSession = Depends(get_session)
) -> ReviewListResponse:
    summary, items = await _svc(session).list(book_id)
    return ReviewListResponse(
        average=summary.average,
        count=summary.count,
        items=[ReviewItem.model_validate(r) for r in items],
    )
