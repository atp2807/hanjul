"""cover API — AI 표지 생성 + 직접 업로드."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.features.catalog.presentation.endpoints import require_book_owner
from src.features.cover.application.cover_service import CoverService
from src.features.cover.domain.ports import BookNotFound
from src.features.cover.presentation.dependencies import get_cover_service
from src.features.cover.presentation.schemas import CoverResponse, GenerateCoverRequest
from src.shared.errors import NotFoundError, ValidationError

router = APIRouter(tags=["cover"])

# 허용 이미지 타입 → 확장자
_IMAGE_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_MAX_BYTES = 5 * 1024 * 1024  # 5MB


@router.post("/books/{book_id}/cover", response_model=CoverResponse)
async def generate_cover(
    book_id: UUID, body: GenerateCoverRequest, svc: CoverService = Depends(get_cover_service)
) -> CoverResponse:
    try:
        url = await svc.generate_for_book(book_id, body.prompt)
    except BookNotFound:
        raise NotFoundError("book not found")
    except RuntimeError as e:
        raise HTTPException(503, str(e))  # 표지 생성 비활성/장애
    return CoverResponse(cover_url=url)


@router.post("/books/{book_id}/cover/upload", response_model=CoverResponse)
async def upload_cover(
    book_id: UUID,
    file: UploadFile = File(...),
    svc: CoverService = Depends(get_cover_service),
    _owner: None = Depends(require_book_owner),  # 소유 작가만 (없는 책 404 / 타인 403)
) -> CoverResponse:
    """작가가 직접 표지 이미지 업로드 (PNG/JPG/WebP, 5MB 이하)."""
    ext = _IMAGE_EXT.get(file.content_type)
    if ext is None:
        raise ValidationError("이미지 파일만 올릴 수 있어요 (PNG·JPG·WebP)")
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise ValidationError("표지 이미지는 5MB 이하여야 해요")
    try:
        url = await svc.upload_for_book(book_id, data, ext)
    except BookNotFound:
        raise NotFoundError("book not found")
    return CoverResponse(cover_url=url)
