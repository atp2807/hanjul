"""books 리포지토리 포트(Protocol) — 도메인이 요구하는 영속성 계약.

구현체: infrastructure.book_repo.SqlBookRepository (운영) / tests 의 FakeBookRepository.
"""
from typing import Protocol
from uuid import UUID

from src.features.books.domain.models import BookView


class BookRepository(Protocol):
    async def create_book(
        self, *, title: str, kind: str, language: str, author_id: UUID | None = None
    ) -> UUID:
        """책을 만들고 id 를 반환. author_id 미지정 = 작가 미배정."""
        ...

    async def book_exists(self, book_id: UUID) -> bool:
        ...

    async def add_chapter_with_blocks(
        self, book_id: UUID, title: str | None, blocks: list[dict]
    ) -> UUID:
        """장 1개 + 블록들을 추가하고 chapter_id 반환. blocks = [{"type","html"}, ...]."""
        ...

    async def get_author_id(self, book_id: UUID) -> UUID | None:
        """책의 작가 id. 책이 없거나 미배정이면 None."""
        ...

    async def set_preview_limit(self, book_id: UUID, limit: int) -> None:
        """무료 미리보기 공개 블록 수 설정."""
        ...

    async def replace_content(self, book_id: UUID, chapters: list[dict]) -> int:
        """책의 모든 장/블록을 주어진 챕터로 교체. 장 수 반환.
        chapters = [{"title": str|None, "blocks": [{"type","html"}]}, ...]."""
        ...

    async def get_content(self, book_id: UUID) -> BookView | None:
        """책 + 장 + 블록 전체를 정렬된 뷰로 반환. 없으면 None."""
        ...

    async def set_content_rating(
        self, book_id: UUID, rating: str, detail: dict[str, str]
    ) -> None:
        """콘텐츠 연령등급(최종) + 8기준 세부를 저장."""
        ...
