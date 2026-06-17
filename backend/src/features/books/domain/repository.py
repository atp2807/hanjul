"""books 리포지토리 포트(Protocol) — 도메인이 요구하는 영속성 계약.

구현체: infrastructure.book_repo.SqlBookRepository (운영) / tests 의 FakeBookRepository.
"""
from typing import Protocol
from uuid import UUID

from src.features.books.domain.models import BookView


class BookRepository(Protocol):
    async def create_book(self, *, title: str, kind: str, language: str) -> UUID:
        """책을 만들고 id 를 반환."""
        ...

    async def book_exists(self, book_id: UUID) -> bool:
        ...

    async def add_chapter_with_blocks(
        self, book_id: UUID, title: str | None, blocks: list[dict]
    ) -> UUID:
        """장 1개 + 블록들을 추가하고 chapter_id 반환. blocks = [{"type","html"}, ...]."""
        ...

    async def get_content(self, book_id: UUID) -> BookView | None:
        """책 + 장 + 블록 전체를 정렬된 뷰로 반환. 없으면 None."""
        ...
