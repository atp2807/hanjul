"""cover 테스트용 Fake — 생성기 + 리포지토리."""
from uuid import UUID


class FakeCoverGenerator:
    def __init__(self, url: str = "https://img.hanjul.io/cover.png"):
        self.url = url
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.url


class FakeCoverRepository:
    def __init__(self) -> None:
        self.existing: set[UUID] = set()
        self.covers: dict[UUID, str] = {}

    def seed(self, book_id: UUID) -> None:
        self.existing.add(book_id)

    async def book_exists(self, book_id: UUID) -> bool:
        return book_id in self.existing

    async def set_cover(self, book_id: UUID, cover_url: str) -> None:
        self.covers[book_id] = cover_url
