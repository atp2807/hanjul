"""cover 도메인 — AI 표지 생성기 + 리포지토리 포트 + 에러."""
from typing import Protocol
from uuid import UUID


class BookNotFound(Exception):
    def __init__(self, book_id: UUID):
        self.book_id = book_id
        super().__init__(f"book not found: {book_id}")


class CoverGenerator(Protocol):
    async def generate(self, prompt: str) -> str:
        """프롬프트로 표지 이미지를 생성하고 그 URL 을 반환."""
        ...


class CoverRepository(Protocol):
    async def book_exists(self, book_id: UUID) -> bool:
        ...

    async def set_cover(self, book_id: UUID, cover_url: str) -> None:
        ...
