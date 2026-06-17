"""인메모리 BookRepository — DB 없이 서비스/엔드포인트 테스트.

BookRepository 포트를 구조적으로 만족한다(Protocol 이라 상속 불필요).
"""
import uuid
from uuid import UUID

from src.features.books.domain.models import BlockView, BookView, ChapterView


class FakeBookRepository:
    def __init__(self) -> None:
        self.books: dict[UUID, dict] = {}      # book_id -> {title, kind, language, status}
        self.chapters: dict[UUID, list[dict]] = {}  # book_id -> [{id,title,order_no,blocks:[...]}]

    async def create_book(self, *, title: str, kind: str, language: str) -> UUID:
        book_id = uuid.uuid4()
        self.books[book_id] = {"title": title, "kind": kind, "language": language, "status": "DRAFT"}
        self.chapters[book_id] = []
        return book_id

    async def book_exists(self, book_id: UUID) -> bool:
        return book_id in self.books

    async def add_chapter_with_blocks(self, book_id: UUID, title, blocks: list[dict]) -> UUID:
        chapter_id = uuid.uuid4()
        order_no = len(self.chapters[book_id])
        self.chapters[book_id].append({
            "id": chapter_id,
            "title": title,
            "order_no": order_no,
            "blocks": [
                {"id": uuid.uuid4(), "order_no": i, "block_type": b["type"], "html": b["html"]}
                for i, b in enumerate(blocks)
            ],
        })
        return chapter_id

    async def get_content(self, book_id: UUID) -> BookView | None:
        meta = self.books.get(book_id)
        if meta is None:
            return None
        return BookView(
            id=book_id,
            title=meta["title"],
            kind=meta["kind"],
            language=meta["language"],
            status=meta["status"],
            chapters=[
                ChapterView(
                    id=c["id"],
                    title=c["title"],
                    order_no=c["order_no"],
                    blocks=[BlockView(**b) for b in c["blocks"]],
                )
                for c in self.chapters[book_id]
            ],
        )
