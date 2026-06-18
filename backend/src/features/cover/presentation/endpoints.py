"""cover API — AI 표지 생성."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.features.cover.application.cover_service import CoverService
from src.features.cover.domain.ports import BookNotFound
from src.features.cover.presentation.dependencies import get_cover_service
from src.features.cover.presentation.schemas import CoverResponse, GenerateCoverRequest

router = APIRouter(tags=["cover"])


@router.post("/books/{book_id}/cover", response_model=CoverResponse)
async def generate_cover(
    book_id: UUID, body: GenerateCoverRequest, svc: CoverService = Depends(get_cover_service)
) -> CoverResponse:
    try:
        url = await svc.generate_for_book(book_id, body.prompt)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except RuntimeError as e:
        raise HTTPException(503, str(e))  # 표지 생성 비활성/장애
    return CoverResponse(cover_url=url)
