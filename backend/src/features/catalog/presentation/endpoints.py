"""catalog API — 출판 라이프사이클(/books) + 스토어(/store)."""
import logging
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
from src.features.notifications.application.notification_service import NotificationService
from src.features.notifications.presentation.dependencies import get_notification_service
from src.features.catalog.presentation.schemas import (
    AssignAuthorRequest,
    AuthorProfileResponse,
    BookSummaryResponse,
    SchedulePublishRequest,
    SetDiscountRequest,
    SetIsbnRequest,
    SetPriceRequest,
    StoreListResponse,
    UpdateMetaRequest,
)

router = APIRouter(tags=["catalog"])
logger = logging.getLogger("app")


def _summary_response(s) -> BookSummaryResponse:
    return BookSummaryResponse.model_validate(s)


async def _notify_followers_new_book(
    svc: CatalogService, notif: NotificationService, book_id: UUID
) -> None:
    """출판 성공 후 작가 팔로워에게 신간 알림 (멱등 — 재발행해도 1회).

    best-effort — 출판은 이미 커밋됐으므로 알림 실패가 응답을 500으로 만들면 안 됨.
    """
    try:
        meta = await svc.get_meta(book_id)
        await notif.notify_new_book(book_id, meta.author_id, meta.title)
    except Exception:
        logger.exception("신간 알림 발송 실패 (book=%s) — 출판은 정상", book_id)


async def require_book_owner(
    book_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CatalogService = Depends(get_catalog_service),
) -> None:
    """책 변경 권한 = 소유 작가만. 없는 책 404 / 타인 403 (fail-closed)."""
    try:
        meta = await svc.get_meta(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    if meta.author_id != principal.id:
        raise HTTPException(403, "not the owner")


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
    book_id: UUID, body: SetPriceRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    try:
        await svc.set_price(book_id, body.amount)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.put("/books/{book_id}/meta", status_code=204)
async def update_meta(
    book_id: UUID, body: UpdateMetaRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    """부제·소개·분류 편집 (스토어 노출·검색 품질)."""
    try:
        await svc.update_meta(book_id, body.subtitle, body.description, body.category)
    except BookNotFound:
        raise HTTPException(404, "book not found")


@router.put("/books/{book_id}/discount", status_code=204)
async def set_discount(
    book_id: UUID, body: SetDiscountRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    """기간 할인 설정 (종료시각까지 할인가 적용)."""
    try:
        await svc.set_discount(book_id, body.amount, body.until)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/books/{book_id}/submit", status_code=204)
async def submit_for_review(
    book_id: UUID, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    try:
        await svc.submit_for_review(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except InvalidTransition as e:
        raise HTTPException(409, str(e))


@router.post("/books/{book_id}/publish", status_code=204)
async def publish(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    notif: NotificationService = Depends(get_notification_service),
    _owner: None = Depends(require_book_owner),
) -> None:
    try:
        await svc.publish(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except InvalidTransition as e:
        raise HTTPException(409, str(e))
    except PriceRequired as e:
        raise HTTPException(422, str(e))
    await _notify_followers_new_book(svc, notif, book_id)


@router.post("/books/{book_id}/unpublish", status_code=204)
async def unpublish(book_id: UUID, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)) -> None:
    """출판 취소 — 스토어에서 비공개로 내림."""
    try:
        await svc.unpublish(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")


@router.post("/books/{book_id}/publish-now", status_code=204)
async def publish_now(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    notif: NotificationService = Depends(get_notification_service),
    _owner: None = Depends(require_book_owner),
) -> None:
    """즉시 출간 (심사 생략)."""
    try:
        await svc.auto_publish(book_id)
    except BookNotFound:
        raise HTTPException(404, "book not found")
    except PriceRequired as e:
        raise HTTPException(422, str(e))
    await _notify_followers_new_book(svc, notif, book_id)


@router.post("/books/{book_id}/schedule", status_code=204)
async def schedule_publish(
    book_id: UUID, body: SchedulePublishRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
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
    book_id: UUID, body: SetIsbnRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
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


# ── 작가 공개 프로필 ──────────────────────────────────
@router.get("/authors/{author_id}", response_model=AuthorProfileResponse)
async def author_profile(
    author_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    session: AsyncSession = Depends(get_session),
) -> AuthorProfileResponse:
    acc = await SqlAccountRepository(session).get_account(author_id)
    if acc is None:
        raise HTTPException(404, "author not found")
    books = await svc.list_published_by_author(author_id)
    return AuthorProfileResponse(
        id=acc.id,
        display_name=acc.display_name,
        bio=acc.bio,
        books=[_summary_response(b) for b in books],
    )


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
