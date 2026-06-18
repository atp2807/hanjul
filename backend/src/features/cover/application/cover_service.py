"""cover 서비스 — 표지 생성 후 책에 연결."""
from uuid import UUID

from src.features.cover.domain.ports import BookNotFound, CoverGenerator, CoverRepository


class CoverService:
    def __init__(self, repo: CoverRepository, generator: CoverGenerator):
        self.repo = repo
        self.generator = generator

    async def generate_for_book(self, book_id: UUID, prompt: str) -> str:
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        cover_url = await self.generator.generate(prompt)
        await self.repo.set_cover(book_id, cover_url)
        return cover_url
