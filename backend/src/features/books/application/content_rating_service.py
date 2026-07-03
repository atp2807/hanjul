"""콘텐츠 연령등급 서비스 — 자동분류 추천 + 작가 오버라이드 저장.

소유자 확인(BookNotFound/NotOwner 재사용) → 분류/병합 → 최종등급(최댓값) 계산 → 저장.
분류기 호출은 포트 뒤(Demo/Anthropic). AI 프롬프트 비용 통제를 위해 본문은 6000자로 컷.
"""
from uuid import UUID

from src.features.books.domain.content_rating import (
    ContentRatingClassifierPort,
    InvalidRatingInput,
    category_keys,
    is_valid_category,
    is_valid_tier,
    overall_rating,
)
from src.features.books.domain.models import BookNotFound, BookView, NotOwner, extract_text
from src.features.books.domain.repository import BookRepository

# AI 프롬프트로 보낼 본문 최대 길이 (비용 통제).
MAX_CLASSIFY_CHARS = 6000


class ContentRatingService:
    def __init__(self, repo: BookRepository, classifier: ContentRatingClassifierPort):
        self.repo = repo
        self.classifier = classifier

    async def _owned_content(self, book_id: UUID, requester_id: UUID) -> BookView:
        """소유 작가 본인만 접근. 없는 책 → BookNotFound, 타인 → NotOwner."""
        if not await self.repo.book_exists(book_id):
            raise BookNotFound(book_id)
        if await self.repo.get_author_id(book_id) != requester_id:
            raise NotOwner(book_id)
        content = await self.repo.get_content(book_id)
        if content is None:  # 존재 확인 직후라 사실상 도달 불가 — 방어적
            raise BookNotFound(book_id)
        return content

    async def suggest_rating(
        self, book_id: UUID, requester_id: UUID
    ) -> tuple[str, dict[str, str]]:
        """본문 기반 자동분류 → 8기준 세부 + 최종등급(최댓값) 저장·반환."""
        content = await self._owned_content(book_id, requester_id)
        text = extract_text(content)[:MAX_CLASSIFY_CHARS]
        raw = await self.classifier.classify(text)  # 미설정/실패 시 RuntimeError → 503
        detail = self._validate_full(raw)
        rating = overall_rating(detail)
        await self.repo.set_content_rating(book_id, rating, detail)
        return rating, detail

    async def set_rating(
        self, book_id: UUID, requester_id: UUID, overrides: dict[str, str]
    ) -> tuple[str, dict[str, str]]:
        """작가 오버라이드(일부/전체) → 기존값과 병합 → 최종등급 재계산·저장·반환."""
        content = await self._owned_content(book_id, requester_id)
        for key, tier in overrides.items():
            if not is_valid_category(key):
                raise InvalidRatingInput(f"알 수 없는 등급 카테고리예요: {key}")
            if not is_valid_tier(tier):
                raise InvalidRatingInput(f"알 수 없는 등급값이에요: {tier}")
        existing = content.content_rating_detail or {}
        merged = {key: "ALL" for key in category_keys()}
        merged.update({k: v for k, v in existing.items() if k in merged})
        merged.update(overrides)
        rating = overall_rating(merged)
        await self.repo.set_content_rating(book_id, rating, merged)
        return rating, merged

    @staticmethod
    def _validate_full(detail: dict[str, str]) -> dict[str, str]:
        """분류기 출력을 8기준 전체로 정규화 — 이상값은 조용히 넘기지 않고 실패시킴."""
        result: dict[str, str] = {}
        for key in category_keys():
            tier = detail.get(key)
            if not is_valid_tier(tier):
                raise InvalidRatingInput(f"등급 분류 결과가 올바르지 않아요 ({key}={tier})")
            result[key] = tier
        return result
