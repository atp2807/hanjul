"""books API 스키마 (Pydantic). 외부 계약은 camelCase (네이밍룰: API 필드=camelCase)."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class CreateBookRequest(_Camel):
    title: str
    kind: str = "BOOK"        # BOOK | WEBNOVEL
    language: str = "ko"


class CreateBookResponse(_Camel):
    book_id: UUID


class ImportTextRequest(_Camel):
    raw_text: str
    chapter_title: str | None = None


class ImportTextResponse(_Camel):
    chapter_id: UUID
    block_count: int


class BlockInput(_Camel):
    type: str   # P | H1 | H2 | H3 | QUOTE | HR (정본 코드)
    html: str


class ChapterInput(_Camel):
    title: str | None = None
    blocks: list[BlockInput] = []


class SetContentRequest(_Camel):
    """에디터 원클릭 출판 — 정본 전체 교체."""
    chapters: list[ChapterInput]


class SetPreviewLimitRequest(_Camel):
    limit: int  # 무료 공개 블록 수


class BlockResponse(_Camel):
    id: UUID
    order_no: int
    block_type: str
    html: str


class ChapterResponse(_Camel):
    id: UUID
    title: str | None
    order_no: int
    blocks: list[BlockResponse]


class BookContentResponse(_Camel):
    id: UUID
    title: str
    kind: str
    language: str
    status: str
    price_amt: int | None = None
    is_preview: bool = False
    chapters: list[ChapterResponse]
