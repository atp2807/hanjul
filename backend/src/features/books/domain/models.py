"""books 도메인 — persistence-agnostic 뷰 모델 + 에러.

리포지토리는 ORM 객체가 아니라 이 dataclass 들을 반환한다 → 서비스/표현 레이어가
SQLAlchemy 에 의존하지 않고, 인메모리 Fake 로 테스트 가능.
"""
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class BlockView:
    id: UUID
    order_no: int
    block_type: str
    html: str


@dataclass
class ChapterView:
    id: UUID
    title: str | None
    order_no: int
    blocks: list[BlockView] = field(default_factory=list)


@dataclass
class BookView:
    id: UUID
    title: str
    kind: str
    language: str
    status: str
    chapters: list[ChapterView] = field(default_factory=list)


@dataclass
class ImportResult:
    chapter_id: UUID
    block_count: int


class BookNotFound(Exception):
    """요청한 책이 존재하지 않음 → 표현 레이어에서 404."""

    def __init__(self, book_id: UUID):
        self.book_id = book_id
        super().__init__(f"book not found: {book_id}")
