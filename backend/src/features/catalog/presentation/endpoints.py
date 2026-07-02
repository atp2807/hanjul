"""catalog API — 출판 라이프사이클(/books) + 스토어(/store)."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.engine.publishing.onix import OnixProduct, build_onix
from src.features.auth.domain.models import AccountPrincipal
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.domain.models import AccountNotFound
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.auth.presentation.dependencies import get_current_account
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import PUBLISHED
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
from src.shared.errors import ConflictError, ForbiddenError, NotFoundError

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


async def _notify_buyers_revision(
    svc: CatalogService, notif: NotificationService, orders: OrderService, book_id: UUID
) -> None:
    """개정판 재발행 후 구매자에게 알림 (best-effort)."""
    try:
        meta = await svc.get_meta(book_id)
        buyers = await orders.buyer_ids(book_id)
        await notif.notify_revision(book_id, meta.title, buyers)
    except Exception:
        logger.exception("개정판 알림 발송 실패 (book=%s) — 출판은 정상", book_id)


async def require_book_owner(
    book_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: CatalogService = Depends(get_catalog_service),
) -> None:
    """책 변경 권한 = 소유 작가만. 없는 책 404(중앙 핸들러) / 타인 403 (fail-closed)."""
    meta = await svc.get_meta(book_id)  # BookNotFound → 404 (중앙 핸들러)
    if meta.author_id != principal.id:
        raise ForbiddenError("not the owner")


# ── 출판 라이프사이클 ─────────────────────────────────
@router.put("/books/{book_id}/author", status_code=204)
async def assign_author(
    book_id: UUID, body: AssignAuthorRequest, svc: CatalogService = Depends(get_catalog_service)
) -> None:
    await svc.assign_author(book_id, body.author_id)


@router.put("/books/{book_id}/price", status_code=204)
async def set_price(
    book_id: UUID, body: SetPriceRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    await svc.set_price(book_id, body.amount)


@router.put("/books/{book_id}/meta", status_code=204)
async def update_meta(
    book_id: UUID, body: UpdateMetaRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    """부제·소개·분류 편집 (스토어 노출·검색 품질)."""
    await svc.update_meta(book_id, body.subtitle, body.description, body.category)


@router.put("/books/{book_id}/discount", status_code=204)
async def set_discount(
    book_id: UUID, body: SetDiscountRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    """기간 할인 설정 (종료시각까지 할인가 적용)."""
    await svc.set_discount(book_id, body.amount, body.until)


@router.post("/books/{book_id}/submit", status_code=204)
async def submit_for_review(
    book_id: UUID, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    await svc.submit_for_review(book_id)


@router.post("/books/{book_id}/publish", status_code=204)
async def publish(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    notif: NotificationService = Depends(get_notification_service),
    _owner: None = Depends(require_book_owner),
) -> None:
    await svc.publish(book_id)
    await _notify_followers_new_book(svc, notif, book_id)


@router.post("/books/{book_id}/unpublish", status_code=204)
async def unpublish(book_id: UUID, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)) -> None:
    """출판 취소 — 스토어에서 비공개로 내림."""
    await svc.unpublish(book_id)


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    orders: OrderService = Depends(get_order_service),
    _owner: None = Depends(require_book_owner),
) -> None:
    """책 삭제 — 소유 작가만. 판매(주문) 이력 있으면 409(출판 취소만 가능)."""
    # 주문 유무는 billing 포트로 확인(스키마 경계 유지). FK RESTRICT는 운영 DB 안전망.
    if await orders.has_any_order(book_id):
        raise ConflictError("판매 이력이 있어 삭제할 수 없어요. 출판 취소만 가능해요.")
    # BookHasOrders(409)는 FK RESTRICT 안전망 — 중앙 핸들러가 매핑.
    await svc.delete_book(book_id)


@router.post("/books/{book_id}/publish-now", status_code=204)
async def publish_now(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    notif: NotificationService = Depends(get_notification_service),
    orders: OrderService = Depends(get_order_service),
    _owner: None = Depends(require_book_owner),
) -> None:
    """즉시 출간 (심사 생략). 이미 출판된 책 재발행 = 개정판 → 구매자 알림."""
    was_published = (await svc.get_meta(book_id)).status == PUBLISHED
    await svc.auto_publish(book_id)
    if was_published:
        await _notify_buyers_revision(svc, notif, orders, book_id)
    else:
        await _notify_followers_new_book(svc, notif, book_id)


@router.post("/books/{book_id}/schedule", status_code=204)
async def schedule_publish(
    book_id: UUID, body: SchedulePublishRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    """예약 발행 — 지정 시각에 자동 게시."""
    await svc.schedule_publish(book_id, body.publish_at)


@router.put("/books/{book_id}/isbn", status_code=204)
async def set_isbn(
    book_id: UUID, body: SetIsbnRequest, svc: CatalogService = Depends(get_catalog_service), _owner: None = Depends(require_book_owner)
) -> None:
    await svc.set_isbn(book_id, body.isbn)


@router.get("/books/{book_id}/onix")
async def book_onix(
    book_id: UUID,
    svc: CatalogService = Depends(get_catalog_service),
    acct: AccountService = Depends(get_account_service),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """책 메타 → ONIX 3.0 XML (서점 유통 표준 피드)."""
    meta = await svc.get_meta(book_id)  # BookNotFound → 404 (중앙 핸들러)
    author = None
    if meta.author_id:
        names = await acct.names_for([meta.author_id])
        author = names.get(meta.author_id)
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
    acct: AccountService = Depends(get_account_service),
) -> AuthorProfileResponse:
    try:
        acc = await acct.get_profile(author_id)
    except AccountNotFound:
        raise NotFoundError("author not found")
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
    category: str | None = None,  # 소설 | 에세이 | ...
    limit: int = 20,
    offset: int = 0,
    svc: CatalogService = Depends(get_catalog_service),
) -> StoreListResponse:
    items = await svc.list_store(q, kind, limit, offset, category)
    return StoreListResponse(items=[_summary_response(s) for s in items], count=len(items))


@router.get("/store/books/{book_id}", response_model=BookSummaryResponse)
async def store_detail(
    book_id: UUID, svc: CatalogService = Depends(get_catalog_service)
) -> BookSummaryResponse:
    s = await svc.get_store_detail(book_id)  # BookNotFound → 404 (중앙 핸들러)
    return _summary_response(s)
