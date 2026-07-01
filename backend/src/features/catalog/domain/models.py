"""catalog 도메인 — 책 요약 뷰 + 출판 상태/에러."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.errors import DomainError

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
    blocked_at: datetime | None = None  # 운영자 takedown 시각 (NULL=정상)


class CatalogError(DomainError):
    """catalog 도메인 예외 베이스."""


class BookNotFound(CatalogError):
    status_code = 404
    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("책을 찾을 수 없어요.")


class InvalidTransition(CatalogError):
    status_code = 409
    def __init__(self, frm: str, to: str):
        super().__init__("현재 상태에서는 진행할 수 없어요.")


class PriceRequired(CatalogError):
    status_code = 422
    def __init__(self):
        super().__init__("출판하려면 가격을 먼저 설정해야 해요.")


class BookHasOrders(CatalogError):
    """주문/판매 이력이 있어 삭제 불가 (구매자 권리 보호)."""
    status_code = 409
    def __init__(self):
        super().__init__("판매 이력이 있어 삭제할 수 없어요. 출판 취소만 가능해요.")
