"""books 도메인 — persistence-agnostic 뷰 모델 + 에러.

리포지토리는 ORM 객체가 아니라 이 dataclass 들을 반환한다 → 서비스/표현 레이어가
SQLAlchemy 에 의존하지 않고, 인메모리 Fake 로 테스트 가능.
"""
from dataclasses import dataclass, field
from uuid import UUID

from src.shared.errors import ForbiddenError, NotFoundError


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
    price_amt: int | None = None
    preview_limit: int = 3
    chapters: list[ChapterView] = field(default_factory=list)


def to_preview(content: BookView, limit: int) -> BookView:
    """앞 limit개 블록만 남긴 미리보기 뷰 (장 경계 가로질러 누적)."""
    remaining = limit
    chapters: list[ChapterView] = []
    for ch in content.chapters:
        if remaining <= 0:
            break
        blocks = ch.blocks[:remaining]
        remaining -= len(blocks)
        chapters.append(ChapterView(id=ch.id, title=ch.title, order_no=ch.order_no, blocks=blocks))
    return BookView(
        id=content.id,
        title=content.title,
        kind=content.kind,
        language=content.language,
        status=content.status,
        price_amt=content.price_amt,
        chapters=chapters,
    )


def suggest_blurb(content: BookView, limit: int = 150) -> str:
    """본문 앞부분에서 소개문을 추천 (HTML 제거·공백 정규화). LLM 고도화는 키 주입 시."""
    import re

    parts = [
        re.sub(r"<[^>]+>", "", b.html)
        for ch in content.chapters
        for b in ch.blocks
        if b.block_type != "HR"
    ]
    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return f"{text[:limit]}…" if len(text) > limit else text


@dataclass
class ImportResult:
    chapter_id: UUID
    block_count: int


class BookNotFound(NotFoundError):
    """요청한 책이 존재하지 않음 → 404."""

    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("책을 찾을 수 없어요.")


class NotOwner(ForbiddenError):
    """책의 작가가 아닌 사용자의 변경 시도 → 403."""

    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("이 책의 작가만 변경할 수 있어요.")
