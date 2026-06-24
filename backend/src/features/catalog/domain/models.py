"""catalog 도메인 — 책 요약 뷰 + 출판 상태/에러."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# 출판 상태 흐름: DRAFT → REVIEW → PUBLISHED
DRAFT = "DRAFT"
REVIEW = "REVIEW"
PUBLISHED = "PUBLISHED"


@dataclass
class BookSummary:
    id: UUID
    title: str
    subtitle: str | None
    author_id: UUID | None
    kind: str
    language: str
    status: str
    price_amt: int | None
    cover_url: str | None
    published_at: datetime | None
    isbn: str | None = None
    description: str | None = None
    category: str | None = None
    discount_amt: int | None = None
    discount_until: datetime | None = None


class CatalogError(Exception):
    pass


class BookNotFound(CatalogError):
    def __init__(self, book_id: UUID):
        self.book_id = book_id
        super().__init__(f"book not found: {book_id}")


class InvalidTransition(CatalogError):
    def __init__(self, frm: str, to: str):
        super().__init__(f"invalid status transition: {frm} -> {to}")


class PriceRequired(CatalogError):
    def __init__(self):
        super().__init__("price must be set before publishing")
