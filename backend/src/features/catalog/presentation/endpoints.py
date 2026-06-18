"""catalog API — 출판 라이프사이클(/books) + 스토어(/store)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import (
    BookNotFound,
    InvalidTransition,
    PriceRequired,
)
from src.features.catalog.presentation.dependencies import get_catalog_service
from src.features.catalog.presentation.schemas import (
    AssignAuthorRequest,
    BookSummaryResponse,
    SetPriceRequest,
    StoreListResponse,
)

router = APIRouter(tags=["catalog"])


def _summary_response(s) -> BookSummaryResponse:
    return BookSummaryResponse.model_validate(s)


# ── 출판 라이프사이클 ─────────────────────────────────
@router.put("/books/{book_id}/author", status_code=204)
async def assign_author(
    book_id: UUID, body: AssignAuthorRequest, svc: CatalogService = Depends(get_catalog_service)
) -> None:
    try:
        await svc.assign_author(book_id, body.author_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")


@router.put("/books/{book_id}/price", status_code=204)
async def set_price(
    book_id: UUID, body: SetPriceRequest, svc: CatalogService = Depends(get_catalog_service)
) -> None:
    try:
        await svc.set_price(book_id, body.amount)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/books/{book_id}/submit", status_code=204)
async def submit_for_review(
    book_id: UUID, svc: CatalogService = Depends(get_catalog_service)
) -> None:
    try:
        await svc.submit_for_review(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except InvalidTransition as e:
        raise HTTPException(409, str(e))


@router.post("/books/{book_id}/publish", status_code=204)
async def publish(book_id: UUID, svc: CatalogService = Depends(get_catalog_service)) -> None:
    try:
        await svc.publish(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except InvalidTransition as e:
        raise HTTPException(409, str(e))
    except PriceRequired as e:
        raise HTTPException(422, str(e))


# ── 스토어 (공개) ─────────────────────────────────────
@router.get("/store/books", response_model=StoreListResponse)
async def store_list(
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    svc: CatalogService = Depends(get_catalog_service),
) -> StoreListResponse:
    items = await svc.list_store(q, limit, offset)
    return StoreListResponse(items=[_summary_response(s) for s in items], count=len(items))


@router.get("/store/books/{book_id}", response_model=BookSummaryResponse)
async def store_detail(
    book_id: UUID, svc: CatalogService = Depends(get_catalog_service)
) -> BookSummaryResponse:
    try:
        s = await svc.get_store_detail(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    return _summary_response(s)
