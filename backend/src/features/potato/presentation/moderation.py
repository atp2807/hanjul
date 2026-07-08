"""potato API — 콘텐츠 모더레이션 (책 강제 비공개/복원 + 감사).

한줄은 셀프퍼블리싱(작가 자가출판)이라 사전 심사 게이트 대신 **사후 takedown**이 핵심.
catalog 서비스에 작업을 위임하고(헥사고날), 여기서 오케스트레이션 + 감사 기록.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import BookNotFound
from src.features.catalog.presentation.dependencies import get_catalog_service
from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    client_ip,
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import (
    BookModerationItem,
    ReviewQueueItem,
    TakedownRequest,
)
from src.features.reports.application.report_service import ReportService
from src.features.reports.presentation.dependencies import get_report_service
from src.shared.errors import NotFoundError

router = APIRouter(prefix="/potato", tags=["potato"])



@router.get("/books", response_model=list[BookModerationItem])
async def list_books(
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _op: OperatorPrincipal = Depends(get_current_operator),
    catalog: CatalogService = Depends(get_catalog_service),
) -> list[BookModerationItem]:
    """모더레이션 브라우저 — 차단 포함 전 상태."""
    items = await catalog.list_for_moderation(status=status, q=q, limit=limit, offset=offset)
    return [
        BookModerationItem(
            id=s.id,
            title=s.title,
            author_id=s.author_id,
            status=s.status,
            blocked=s.blocked_at is not None,
            blocked_at=s.blocked_at,
            published_at=s.published_at,
        )
        for s in items
    ]


@router.post("/books/{book_id}/takedown", status_code=204)
async def takedown(
    book_id: UUID,
    request: Request,
    body: TakedownRequest = TakedownRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    catalog: CatalogService = Depends(get_catalog_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """강제 비공개 — 스토어/작가 프로필에서 즉시 내림."""
    try:
        await catalog.takedown(book_id)
    except BookNotFound:
        raise NotFoundError("book not found")
    await audit.record(op.id, "TAKEDOWN", "BOOK", book_id, {"reason": body.reason}, client_ip(request))


@router.get("/review-queue", response_model=list[ReviewQueueItem])
async def review_queue(
    _op: OperatorPrincipal = Depends(get_current_operator),
    catalog: CatalogService = Depends(get_catalog_service),
    reports: ReportService = Depends(get_report_service),
) -> list[ReviewQueueItem]:
    """운영자 사후 검토 큐 — AGE18 발행책 + OPEN 신고책(조회 전용, 새 상태/전이 없음).

    새 조치 엔드포인트는 만들지 않는다 — 운영자는 이 목록에서 기존 takedown/restore로 조치.
    """
    merged: dict = {}

    for s in await catalog.list_published_with_rating("AGE18"):
        merged[s.id] = ReviewQueueItem(
            book_id=s.id,
            title=s.title,
            author_id=s.author_id,
            rating=s.content_rating,
            reasons=["AGE18"],
            published_at=s.published_at,
        )

    for book_id in await reports.list_open_targets("BOOK"):
        if book_id in merged:
            merged[book_id].reasons.append("REPORTED")
            continue
        try:
            s = await catalog.get_meta(book_id)
        except BookNotFound:
            continue  # 신고 대상 책이 이미 삭제됨 — 조용히 스킵
        merged[book_id] = ReviewQueueItem(
            book_id=s.id,
            title=s.title,
            author_id=s.author_id,
            rating=s.content_rating,
            reasons=["REPORTED"],
            published_at=s.published_at,
        )

    return list(merged.values())


@router.post("/books/{book_id}/restore", status_code=204)
async def restore(
    book_id: UUID,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    catalog: CatalogService = Depends(get_catalog_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """takedown 해제."""
    try:
        await catalog.restore(book_id)
    except BookNotFound:
        raise NotFoundError("book not found")
    await audit.record(op.id, "RESTORE", "BOOK", book_id, None, client_ip(request))
