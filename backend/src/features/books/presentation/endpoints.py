"""books API 엔드포인트."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.features.books.application.book_service import BookService
from src.features.books.domain.models import BookNotFound
from src.features.books.presentation.dependencies import get_book_service
from src.features.books.presentation.schemas import (
    BookContentResponse,
    CreateBookRequest,
    CreateBookResponse,
    ImportTextRequest,
    ImportTextResponse,
)

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=CreateBookResponse, status_code=201)
async def create_book(
    body: CreateBookRequest, service: BookService = Depends(get_book_service)
) -> CreateBookResponse:
    book_id = await service.create_book(title=body.title, kind=body.kind, language=body.language)
    return CreateBookResponse(book_id=book_id)


@router.post("/{book_id}/import", response_model=ImportTextResponse)
async def import_text(
    book_id: UUID,
    body: ImportTextRequest,
    service: BookService = Depends(get_book_service),
) -> ImportTextResponse:
    try:
        result = await service.import_text(book_id, body.raw_text, body.chapter_title)
    except BookNotFound:
        raise HTTPException(status_code=404, detail="book not found")
    return ImportTextResponse(chapter_id=result.chapter_id, block_count=result.block_count)


@router.get("/{book_id}/content", response_model=BookContentResponse)
async def get_content(
    book_id: UUID, service: BookService = Depends(get_book_service)
) -> BookContentResponse:
    try:
        content = await service.get_content(book_id)
    except BookNotFound:
        raise HTTPException(status_code=404, detail="book not found")
    return BookContentResponse.model_validate(content)
