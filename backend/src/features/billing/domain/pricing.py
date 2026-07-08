"""책 가격 조회 포트 — 주문 금액을 서버에서 도출하기 위함 (클라 신뢰 금지)."""
from typing import Protocol
from uuid import UUID


class BookPricing(Protocol):
    async def get_purchasable_price(self, book_id: UUID) -> int | None:
        """출판되고 가격이 설정된 책이면 그 가격(원), 아니면 None(구매 불가)."""
        ...


class BookRatingLookup(Protocol):
    """연령 게이트(dc-daeb0d3d)용 — 주문 시점 책 등급 조회. SqlBookPricing이 겸해서 구현."""

    async def get_content_rating(self, book_id: UUID) -> str | None:
        """책의 content_rating_cd. 책이 없으면 None."""
        ...
