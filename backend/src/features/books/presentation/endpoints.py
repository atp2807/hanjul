"""books API 엔드포인트."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from src.engine.publishing.epub import EpubBook, EpubChapter, build_epub
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import (
    get_current_account,
    get_current_account_optional,
)
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.books.application.book_service import BookService
from src.features.books.domain.models import suggest_blurb, to_preview
from src.features.books.presentation.dependencies import get_book_service
from src.features.books.presentation.schemas import (
    BookContentResponse,
    CreateBookRequest,
    CreateBookResponse,
    ImportTextRequest,
    ImportTextResponse,
    SetContentRequest,
    SetPreviewLimitRequest,
)

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=CreateBookResponse, status_code=201)
async def create_book(
    body: CreateBookRequest,
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
    service: BookService = Depends(get_book_service),
) -> CreateBookResponse:
    # 로그인 상태면 작가 = 현재 사용자
    author_id = principal.id if principal else None
    book_id = await service.create_book(
        title=body.title, kind=body.kind, language=body.language, author_id=author_id
    )
    return CreateBookResponse(book_id=book_id)


@router.post("/{book_id}/import", response_model=ImportTextResponse)
async def import_text(
    book_id: UUID,
    body: ImportTextRequest,
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
    service: BookService = Depends(get_book_service),
) -> ImportTextResponse:
    """원고 import — 소유자 있는 책은 작가 본인만(남의 책에 장 추가 차단).

    BookNotFound 404·NotOwner 403 → 중앙 핸들러가 매핑.
    """
    result = await service.import_text(
        book_id, body.raw_text, body.chapter_title, principal.id if principal else None
    )
    return ImportTextResponse(chapter_id=result.chapter_id, block_count=result.block_count)


@router.get("/{book_id}/suggest-blurb")
async def suggest_blurb_endpoint(
    book_id: UUID, service: BookService = Depends(get_book_service)
) -> dict:
    """본문 기반 소개문 추천 (작가가 검토 후 저장). BookNotFound → 404 (중앙 핸들러)."""
    content = await service.get_content(book_id)
    return {"blurb": suggest_blurb(content)}


@router.put("/{book_id}/content", status_code=204)
async def set_content(
    book_id: UUID,
    body: SetContentRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    service: BookService = Depends(get_book_service),
) -> None:
    """에디터 원클릭 출판 — 정본 전체를 헤딩 기준 챕터로 교체. 작가 본인만."""
    chapters = [
        {"title": c.title, "blocks": [{"type": b.type, "html": b.html} for b in c.blocks]}
        for c in body.chapters
    ]
    # BookNotFound 404·NotOwner 403 → 중앙 핸들러
    await service.set_content(book_id, chapters, principal.id)


@router.put("/{book_id}/preview-limit", status_code=204)
async def set_preview_limit(
    book_id: UUID,
    body: SetPreviewLimitRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    service: BookService = Depends(get_book_service),
) -> None:
    """무료 미리보기 공개 분량(블록 수) 설정 — 작가 본인만. 404/403 → 중앙 핸들러."""
    await service.set_preview_limit(book_id, body.limit, principal.id)


@router.get("/{book_id}/content", response_model=BookContentResponse)
async def get_content(
    book_id: UUID,
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
    service: BookService = Depends(get_book_service),
    orders: OrderService = Depends(get_order_service),
) -> BookContentResponse:
    content = await service.get_content(book_id)  # BookNotFound → 404 (중앙 핸들러)

    is_free = content.price_amt in (None, 0)
    owned = principal is not None and await orders.owns(principal.id, book_id)

    if is_free or owned:
        resp = BookContentResponse.model_validate(content)
        resp.is_preview = False
        return resp

    resp = BookContentResponse.model_validate(to_preview(content, content.preview_limit))
    resp.is_preview = True
    return resp


@router.get("/{book_id}/epub")
async def download_epub(
    book_id: UUID, service: BookService = Depends(get_book_service)
) -> Response:
    """정본 → EPUB 3 파일 다운로드 (서점 유통·소장의 기본 산출물). 404 → 중앙 핸들러."""
    content = await service.get_content(book_id)

    epub_book = EpubBook(
        title=content.title,
        language=content.language,
        identifier=f"urn:uuid:{content.id}",  # ISBN 연동은 #14에서
        chapters=[
            EpubChapter(title=ch.title, html="\n".join(b.html for b in ch.blocks))
            for ch in content.chapters
        ],
    )
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = build_epub(epub_book, modified)
    return Response(
        content=data,
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="{content.id}.epub"'},
    )
