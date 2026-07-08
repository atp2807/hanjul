"""manuscript API — 데스크탑 IDE 원고 백업(일방향 push) + 최신 상태 조회.

인증 필수(get_current_account) — 데스크탑 백업은 로그인 사용자 전용이다(publisher.py의
발행 흐름과 동일하게 Bearer 토큰). sync_key 로 책을 찾고, 없으면 요청자 소유로 새로
만들고, 있는데 다른 계정 소유면 403(NotManuscriptOwner → main.py 중앙 핸들러가 매핑).
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.manuscript.application.manuscript_service import ManuscriptService
from src.features.manuscript.domain.models import ChapterPush
from src.features.manuscript.presentation.dependencies import get_manuscript_service
from src.features.manuscript.presentation.schemas import (
    ChapterStateResponse,
    ManuscriptPushRequest,
    ManuscriptPushResponse,
    ManuscriptStateResponse,
)

router = APIRouter(prefix="/manuscripts", tags=["manuscript"])


@router.put("/{sync_key}", response_model=ManuscriptPushResponse)
async def push_manuscript(
    sync_key: UUID,
    body: ManuscriptPushRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: ManuscriptService = Depends(get_manuscript_service),
) -> ManuscriptPushResponse:
    result = await svc.push(
        principal.id,
        sync_key,
        body.title,
        [
            ChapterPush(
                chapter_key=c.chapter_key, title=c.title, html=c.html, content_hash=c.content_hash
            )
            for c in body.chapters
        ],
    )
    return ManuscriptPushResponse(saved_count=result.saved_count, skipped_count=result.skipped_count)


@router.get("/{sync_key}", response_model=ManuscriptStateResponse)
async def get_manuscript(
    sync_key: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: ManuscriptService = Depends(get_manuscript_service),
) -> ManuscriptStateResponse:
    book, chapters = await svc.get_state(principal.id, sync_key)
    return ManuscriptStateResponse(
        sync_key=book.sync_key,
        title=book.title,
        chapters=[
            ChapterStateResponse(
                chapter_key=c.chapter_key, title=c.title, html=c.html,
                content_hash=c.content_hash, updated_at=c.updated_at,
            )
            for c in chapters
        ],
    )
