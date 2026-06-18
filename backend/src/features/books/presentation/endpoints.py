"""books API 엔드포인트."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account_optional
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.books.application.book_service import BookService
from src.features.books.domain.models import BookNotFound, to_preview
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


# 미구매·미로그인 독자에게 보여줄 미리보기 블록 수
PREVIEW_BLOCK_LIMIT = 3


@router.get("/{book_id}/content", response_model=BookContentResponse)
async def get_content(
    book_id: UUID,
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
    service: BookService = Depends(get_book_service),
    orders: OrderService = Depends(get_order_service),
) -> BookContentResponse:
    try:
        content = await service.get_content(book_id)
    except BookNotFound:
        raise HTTPException(status_code=404, detail="book not found")

    is_free = content.price_amt in (None, 0)
    owned = principal is not None and await orders.owns(principal.id, book_id)

    if is_free or owned:
        resp = BookContentResponse.model_validate(content)
        resp.is_preview = False
        return resp

    resp = BookContentResponse.model_validate(to_preview(content, PREVIEW_BLOCK_LIMIT))
    resp.is_preview = True
    return resp
