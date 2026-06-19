"""catalog API — 출판 라이프사이클(/books) + 스토어(/store)."""
from uuid import UUID

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.engine.publishing.onix import OnixProduct, build_onix
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.infrastructure.account_repo import SqlAccountRepository
from src.features.auth.presentation.dependencies import get_current_account
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
    SchedulePublishRequest,
    SetIsbnRequest,
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


@router.post("/books/{book_id}/publish-now", status_code=204)
async def publish_now(book_id: UUID, svc: CatalogService = Depends(get_catalog_service)) -> None:
    """즉시 출간 (심사 생략)."""
    try:
        await svc.auto_publish(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except PriceRequired as e:
        raise HTTPException(422, str(e))


@router.post("/books/{book_id}/schedule", status_code=204)
async def schedule_publish(
    book_id: UUID, body: SchedulePublishRequest, svc: CatalogService = Depends(get_catalog_service)
) -> None:
    """예약 발행 — 지정 시각에 자동 게시."""
    try:
        await svc.schedule_publish(book_id, body.publish_at)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except PriceRequired as e:
        raise HTTPException(422, str(e))


@router.put("/books/{book_id}/isbn", status_code=204)
async def set_isbn(
    book_id: UUID, body: SetIsbnRequest, svc: CatalogService = Depends(get_catalog_service)
) -> None:
    try:
        await svc.set_isbn(book_id, body.isbn)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/books/{book_id}/onix")
async def book_onix(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """책 메타 → ONIX 3.0 XML (서점 유통 표준 피드)."""
    try:
        meta = await svc.get_meta(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    author = None
    if meta.author_id:
        acc = await SqlAccountRepository(session).get_account(meta.author_id)
        author = acc.display_name if acc else None
    product = OnixProduct(
        record_reference=str(meta.id),
        title=meta.title,
        language=meta.language,
        isbn=meta.isbn,
        author=author,
        price_amt=meta.price_amt,
    )
    xml = build_onix(product, datetime.now(timezone.utc).strftime("%Y%m%d"))
    return Response(content=xml, media_type="application/xml")


# ── 작가 스튜디오 (내 책, 인증) ───────────────────────
@router.get("/me/books", response_model=StoreListResponse)
async def my_books(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CatalogService = Depends(get_catalog_service),
) -> StoreListResponse:
    items = await svc.list_my_books(principal.id)
    return StoreListResponse(items=[_summary_response(s) for s in items], count=len(items))


# ── 스토어 (공개) ─────────────────────────────────────
@router.get("/store/books", response_model=StoreListResponse)
async def store_list(
    q: str | None = None,
    kind: str | None = None,  # BOOK | WEBNOVEL
    limit: int = 20,
    offset: int = 0,
    svc: CatalogService = Depends(get_catalog_service),
) -> StoreListResponse:
    items = await svc.list_store(q, kind, limit, offset)
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
