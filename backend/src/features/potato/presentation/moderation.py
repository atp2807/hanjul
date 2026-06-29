"""potato API — 콘텐츠 모더레이션 (책 강제 비공개/복원 + 감사).

한줄은 셀프퍼블리싱(작가 자가출판)이라 사전 심사 게이트 대신 **사후 takedown**이 핵심.
catalog 서비스에 작업을 위임하고(헥사고날), 여기서 오케스트레이션 + 감사 기록.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.domain.models import BookNotFound
from src.features.catalog.presentation.dependencies import get_catalog_service
from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import BookModerationItem, TakedownRequest

router = APIRouter(prefix="/potato", tags=["potato"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


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
        raise HTTPException(404, "book not found")
    await audit.record(op.id, "TAKEDOWN", "BOOK", book_id, {"reason": body.reason}, _client_ip(request))


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
        raise HTTPException(404, "book not found")
    await audit.record(op.id, "RESTORE", "BOOK", book_id, None, _client_ip(request))
