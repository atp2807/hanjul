"""books API 엔드포인트."""
import logging
from datetime import UTC, datetime
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
from src.features.books.domain.models import NotPurchased, suggest_blurb, to_preview
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


async def _best_effort_mark_delivered(orders: OrderService, buyer_id: UUID, book_id: UUID) -> None:
    """전자책 제공 개시 기록 — 실패해도 열람/다운로드 자체를 막으면 안 된다(환불세이프 게이트용).

    회귀가드: 여기서 예외를 삼키지 않으면 DB 문제 하나로 정상 구매자가 자기 책을 못 읽게 된다
    (부가 회계기록이 핵심 기능을 막는 회귀) — 절대 전파 금지, 로그만 남긴다.
    """
    try:
        await orders.mark_delivered(buyer_id, book_id)
    except Exception:
        logger.warning(
            "mark_delivered 실패 (book=%s, buyer=%s) — 열람/다운로드는 계속 진행",
            book_id, buyer_id, exc_info=True,
        )


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
    # BookNotFound 404·AgeVerificationRequired 403(dc-daeb0d3d) → 중앙 핸들러
    content = await service.get_content(book_id, principal.id if principal else None)

    is_free = content.price_amt in (None, 0)
    owned = principal is not None and await orders.owns(principal.id, book_id)
    if owned and principal is not None:
        # 구매자 본인의 전체 열람 = 제공 개시(환불세이프 게이트, payout_repo._unpaid_stmt).
        await _best_effort_mark_delivered(orders, principal.id, book_id)

    if is_free or owned:
        resp = BookContentResponse.model_validate(content)
        resp.is_preview = False
        return resp

    resp = BookContentResponse.model_validate(to_preview(content, content.preview_limit))
    resp.is_preview = True
    return resp


@router.get("/{book_id}/epub")
async def download_epub(
    book_id: UUID,
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
    service: BookService = Depends(get_book_service),
    orders: OrderService = Depends(get_order_service),
) -> Response:
    """정본 → EPUB 3 파일 다운로드 (서점 유통·소장의 기본 산출물).

    ⚠️ 회귀가드: 이전엔 인증·구매 확인이 전혀 없어 book_id(스토어 URL에 노출)만 알면 누구나
    무료로 전체 EPUB을 받을 수 있었다(2026-07-08 연령게이트 감사 중 발견). get_content의
    is_free/owned 판정을 /content 엔드포인트와 동일하게 적용하되, **저자 본인은 우회**한다 —
    이 엔드포인트의 유일한 실사용처가 스튜디오 "EPUB 내려받기"(자기 책 자체출력)라, 저자가
    자기 유료책을 구매 없이 못 받으면 그 자체가 회귀(실제로 e2e 작가여정이 이걸로 깨졌었음).
    미리보기 개념이 없는 경로라 그 외엔 미구매·유료면 전면 차단(NotPurchased).
    BookNotFound·AgeVerificationRequired·NotPurchased → 중앙 핸들러.
    """
    content = await service.get_content(book_id, principal.id if principal else None)
    is_free = content.price_amt in (None, 0)
    owned = principal is not None and await orders.owns(principal.id, book_id)
    is_author = await service.is_author(book_id, principal.id if principal else None)
    if not (is_free or owned or is_author):
        raise NotPurchased(book_id)
    if owned and principal is not None:
        # 구매자 본인의 EPUB 다운로드 = 제공 개시(환불세이프 게이트). 저자 본인 우회는 구매가
        # 아니므로 대상 아님(is_author만으로 통과한 경우 mark_delivered 호출 안 함).
        await _best_effort_mark_delivered(orders, principal.id, book_id)

    epub_book = EpubBook(
        title=content.title,
        language=content.language,
        identifier=f"urn:uuid:{content.id}",  # ISBN 연동은 #14에서
        chapters=[
            EpubChapter(title=ch.title, html="\n".join(b.html for b in ch.blocks))
            for ch in content.chapters
        ],
    )
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = build_epub(epub_book, modified)
    return Response(
        content=data,
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="{content.id}.epub"'},
    )
