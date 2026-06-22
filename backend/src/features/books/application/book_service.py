"""books 애플리케이션 서비스 — 유스케이스 오케스트레이션.

순수 변환(engine)과 영속성(repository port)을 조합한다. 프레임워크/DB 직접 의존 없음.
"""
from uuid import UUID

from src.engine.imports.text_to_blocks import text_to_blocks
from src.features.books.domain.models import BookNotFound, BookView, ImportResult, NotOwner
from src.features.books.domain.repository import BookRepository


class BookService:
    def __init__(self, repo: BookRepository):
        self.repo = repo

    async def create_book(
        self, *, title: str, kind: str = "BOOK", language: str = "ko", author_id: UUID | None = None
    ) -> UUID:
        return await self.repo.create_book(
            title=title, kind=kind, language=language, author_id=author_id
        )

    async def import_text(
        self, book_id: UUID, raw_text: str, chapter_title: str | None = None
    ) -> ImportResult:
        """원고 텍스트를 정본 HTML 블록으로 변환해 새 장으로 저장."""
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        blocks = text_to_blocks(raw_text)
        chapter_id = await self.repo.add_chapter_with_blocks(book_id, chapter_title, blocks)
        return ImportResult(chapter_id=chapter_id, block_count=len(blocks))

    async def set_content(
        self, book_id: UUID, chapters: list[dict], requester_id: UUID
    ) -> int:
        """책의 정본 전체를 교체 (에디터 원클릭 출판). 작가 본인만 허용. 장 수 반환."""
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        if await self.repo.get_author_id(book_id) != requester_id:
            raise NotOwner(book_id)
        return await self.repo.replace_content(book_id, chapters)

    async def get_content(self, book_id: UUID) -> BookView:
        content = await self.repo.get_content(book_id)
        if content is None:
            raise BookNotFound(book_id)
        return content
