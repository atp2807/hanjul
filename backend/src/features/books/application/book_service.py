"""books 애플리케이션 서비스 — 유스케이스 오케스트레이션.

순수 변환(engine)과 영속성(repository port)을 조합한다. 프레임워크/DB 직접 의존 없음.
"""
from uuid import UUID

from src.engine.imports.block_html import InvalidBlockHtml, validate_block_html
from src.engine.imports.text_to_blocks import text_to_blocks
from src.features.books.domain.content_rating import (
    AccountTierLookup,
    AgeVerificationRequired,
    is_book_accessible,
)
from src.features.books.domain.models import BookNotFound, BookView, ImportResult, NotOwner
from src.features.books.domain.repository import BookRepository
from src.shared.errors import ValidationError


class BookService:
    def __init__(self, repo: BookRepository, account_tier: AccountTierLookup | None = None):
        self.repo = repo
        # 연령 게이트(dc-daeb0d3d) 포트 — 미주입이면 "ALL"로 간주(fail-closed 기본값).
        # 실제 요청 경로(get_book_service DI)는 항상 채워 인증계정의 실제 등급을 조회한다.
        self.account_tier = account_tier

    async def create_book(
        self, *, title: str, kind: str = "BOOK", language: str = "ko", author_id: UUID | None = None
    ) -> UUID:
        return await self.repo.create_book(
            title=title, kind=kind, language=language, author_id=author_id
        )

    async def import_text(
        self,
        book_id: UUID,
        raw_text: str,
        chapter_title: str | None = None,
        requester_id: UUID | None = None,
    ) -> ImportResult:
        """원고 텍스트를 정본 HTML 블록으로 변환해 새 장으로 저장.

        소유자 있는 책은 작가 본인만 import 가능(남의 책에 장 추가 차단).
        소유자 없는(익명) 책은 개방 — 로그인 전 작성/데모 흐름용.
        """
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        author_id = await self.repo.get_author_id(book_id)
        if author_id is not None and author_id != requester_id:
            raise NotOwner(book_id)
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
        # 신뢰 못 하는 클라이언트가 보낸 html — 정본 문법 검증(하나라도 걸리면 전체 거부).
        for chapter in chapters:
            for block in chapter["blocks"]:
                try:
                    validate_block_html(block["type"], block["html"])
                except InvalidBlockHtml:
                    raise ValidationError("본문 형식이 올바르지 않아요.") from None
        return await self.repo.replace_content(book_id, chapters)

    async def set_preview_limit(self, book_id: UUID, limit: int, requester_id: UUID) -> None:
        """무료 미리보기 공개 블록 수 — 작가 본인만. 음수 금지."""
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        if await self.repo.get_author_id(book_id) != requester_id:
            raise NotOwner(book_id)
        await self.repo.set_preview_limit(book_id, max(0, limit))

    async def is_author(self, book_id: UUID, account_id: UUID | None) -> bool:
        """저자 본인 여부 — EPUB 다운로드 등 '구매 게이트를 저자는 우회' 판정에 재사용."""
        if account_id is None:
            return False
        return await self.repo.get_author_id(book_id) == account_id

    async def get_content(self, book_id: UUID, account_id: UUID | None = None) -> BookView:
        content = await self.repo.get_content(book_id)
        if content is None:
            raise BookNotFound(book_id)
        # 연령 게이트(dc-daeb0d3d) — 소유 작가는 항상 열람 가능(본인이 쓰고 등급 매긴 원고를
        # 에디터에서 못 여는 건 말이 안 됨). 그 외엔 항상 검사하되 tier는 fail-closed 기본값 "ALL".
        # 포트 미주입/비로그인이면 조회를 생략하고 "ALL"로 간주(가장 낮은 등급만 통과) —
        # ALL 등급 책(기존 테스트 더블의 기본값)엔 영향 없고, 등급 있는 책만 실제로 막힌다.
        author_id = await self.repo.get_author_id(book_id)
        is_owner = account_id is not None and account_id == author_id
        if not is_owner:
            tier = "ALL"
            if self.account_tier is not None and account_id is not None:
                tier = await self.account_tier.get_verified_tier(account_id)
            if not is_book_accessible(content.content_rating, tier):
                raise AgeVerificationRequired()
        return content
