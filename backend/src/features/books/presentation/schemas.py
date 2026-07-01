"""books API 스키마 (Pydantic). 외부 계약은 camelCase (네이밍룰: API 필드=camelCase)."""
from uuid import UUID

from src.presentation.schema import CamelSchema


class CreateBookRequest(CamelSchema):
    title: str
    kind: str = "BOOK"        # BOOK | WEBNOVEL
    language: str = "ko"


class CreateBookResponse(CamelSchema):
    book_id: UUID


class ImportTextRequest(CamelSchema):
    raw_text: str
    chapter_title: str | None = None


class ImportTextResponse(CamelSchema):
    chapter_id: UUID
    block_count: int


class BlockInput(CamelSchema):
    type: str   # P | H1 | H2 | H3 | QUOTE | HR (정본 코드)
    html: str


class ChapterInput(CamelSchema):
    title: str | None = None
    blocks: list[BlockInput] = []


class SetContentRequest(CamelSchema):
    """에디터 원클릭 출판 — 정본 전체 교체."""
    chapters: list[ChapterInput]


class SetPreviewLimitRequest(CamelSchema):
    limit: int  # 무료 공개 블록 수


class BlockResponse(CamelSchema):
    id: UUID
    order_no: int
    block_type: str
    html: str


class ChapterResponse(CamelSchema):
    id: UUID
    title: str | None
    order_no: int
    blocks: list[BlockResponse]


class BookContentResponse(CamelSchema):
    id: UUID
    title: str
    kind: str
    language: str
    status: str
    price_amt: int | None = None
    is_preview: bool = False
    chapters: list[ChapterResponse]
