"""cover 서비스 — 표지 생성 후 책에 연결."""
from uuid import UUID

from src.features.cover.domain.ports import BookNotFound, CoverGenerator, CoverRepository


class CoverService:
    def __init__(self, repo: CoverRepository, generator: CoverGenerator, storage=None):
        self.repo = repo
        self.generator = generator
        self.storage = storage

    async def generate_for_book(self, book_id: UUID, prompt: str) -> str:
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        cover_url = await self.generator.generate(prompt, reference=str(book_id))
        await self.repo.set_cover(book_id, cover_url)
        return cover_url

    async def upload_for_book(self, book_id: UUID, data: bytes, ext: str) -> str:
        """작가가 올린 표지 이미지 → 저장소에 보관하고 책에 연결."""
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        cover_url = await self.storage.save(data, ext)
        await self.repo.set_cover(book_id, cover_url)
        return cover_url
