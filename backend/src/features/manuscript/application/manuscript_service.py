"""manuscript 애플리케이션 서비스 — push(백업 수신)/get_state(최신 상태 조회)."""
from uuid import UUID

from src.features.manuscript.domain.models import (
    ChapterPush,
    ChapterState,
    ManuscriptBookView,
    ManuscriptNotFound,
    ManuscriptRepository,
    NotManuscriptOwner,
    PushResult,
)


class ManuscriptService:
    def __init__(self, repo: ManuscriptRepository):
        self.repo = repo

    async def push(
        self, account_id: UUID, sync_key: UUID, title: str, chapters: list[ChapterPush]
    ) -> PushResult:
        """책이 없으면 생성(소유=요청자), 있으면 소유자 일치 확인 후 제목 갱신.

        챕터는 각각 독립적으로 dedup 판정(같은 요청 안에서도 챕터별로 저장/스킵이 갈릴 수
        있음) — repo.push_chapter 가 최신 리비전과 content_hash 를 비교해 저장 여부를 정한다.
        """
        book = await self.repo.get_book_by_sync_key(sync_key)
        if book is None:
            book = await self.repo.create_book(account_id, sync_key, title)
        else:
            if book.account_id != account_id:
                raise NotManuscriptOwner()
            await self.repo.touch_book(book.id, title)

        saved = 0
        skipped = 0
        for chapter in chapters:
            did_save = await self.repo.push_chapter(
                book.id, chapter.chapter_key, chapter.title, chapter.html, chapter.content_hash
            )
            if did_save:
                saved += 1
            else:
                skipped += 1
        return PushResult(saved_count=saved, skipped_count=skipped)

    async def get_state(
        self, account_id: UUID, sync_key: UUID
    ) -> tuple[ManuscriptBookView, list[ChapterState]]:
        book = await self.repo.get_book_by_sync_key(sync_key)
        if book is None:
            raise ManuscriptNotFound()
        if book.account_id != account_id:
            raise NotManuscriptOwner()
        chapters = await self.repo.latest_state(book.id)
        return book, chapters
