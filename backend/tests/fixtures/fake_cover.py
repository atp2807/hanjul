"""cover 테스트용 Fake — 생성기 + 리포지토리."""
from uuid import UUID


class FakeCoverGenerator:
    def __init__(self, url: str = "https://img.hanjul.io/cover.png"):
        self.url = url
        self.prompts: list[str] = []
        self.references: list[str] = []

    async def generate(self, prompt: str, reference: str) -> str:
        self.prompts.append(prompt)
        self.references.append(reference)
        return self.url


class FakeCoverStorage:
    """업로드 표지 저장 Fake — 디스크 안 쓰고 기록만."""
    def __init__(self) -> None:
        self.saved: list[tuple[int, str]] = []  # (바이트수, ext)

    async def save(self, data: bytes, ext: str) -> str:
        self.saved.append((len(data), ext))
        return f"https://img.hanjul.io/uploads/covers/fake.{ext}"


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
