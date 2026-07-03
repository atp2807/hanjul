"""콘텐츠 연령등급 도메인 — 4단계 서수 tier + 8기준 분류 포트 + 기준 로더.

한국은 게임·영화와 달리 웹소설·웹툰에 정부 사전승인 기관이 없어 **플랫폼 자율등급**이
관행. 기준 초안은 ``content_rating_criteria.json`` (한국만화영상진흥원 acw.or.kr 8기준×
4단계 틀 참고) — 코드는 그 파일을 **읽기만** 하고 절대 고치지 않는다(_note: 전문가 검수 필요).

최종 등급 = 8개 카테고리 tier 중 **최댓값**(제일 엄격한 것).
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from src.shared.errors import ValidationError

_CRITERIA_PATH = Path(__file__).resolve().parent / "content_rating_criteria.json"

# 서수 tier — 낮음 < 높음. 최종등급 = max(rank).
TIERS: tuple[str, ...] = ("ALL", "AGE12", "AGE15", "AGE18")
_TIER_RANK = {tier: i for i, tier in enumerate(TIERS)}


@lru_cache(maxsize=1)
def load_criteria() -> dict:
    """기준 JSON 로드(캐싱). 파일 내용은 초안 — 코드는 읽기만 한다."""
    return json.loads(_CRITERIA_PATH.read_text(encoding="utf-8"))


def category_keys() -> list[str]:
    """8개 기준 카테고리 key 목록 (theme·violence·…)."""
    return [c["key"] for c in load_criteria()["categories"]]


def is_valid_tier(tier: str) -> bool:
    return tier in _TIER_RANK


def is_valid_category(key: str) -> bool:
    return key in category_keys()


def tier_rank(tier: str) -> int:
    """tier의 서수 순위. 알 수 없는 값이면 ValueError."""
    try:
        return _TIER_RANK[tier]
    except KeyError:
        raise ValueError(f"unknown tier: {tier}") from None


def max_tier(tiers) -> str:
    """여러 tier 중 가장 엄격한(높은) 것. 비어 있으면 ALL."""
    ranked = list(tiers)
    if not ranked:
        return "ALL"
    return max(ranked, key=tier_rank)


def overall_rating(detail: dict[str, str]) -> str:
    """카테고리별 등급 dict → 최종등급(최댓값). 비어 있으면 ALL."""
    return max_tier(detail.values())


class InvalidRatingInput(ValidationError):
    """카테고리 key 또는 tier 값이 유효하지 않음 → 422."""

    default_detail = "등급 입력이 올바르지 않아요."


class ContentRatingClassifierPort(Protocol):
    async def classify(self, text: str) -> dict[str, str]:
        """본문 텍스트를 8개 카테고리 key→tier dict로 분류.

        결과는 category_keys() 전부를 키로, 값은 TIERS 중 하나여야 한다.
        미설정/외부실패 시 RuntimeError(또는 예외)를 던진다 — 표현층이 503으로 매핑.
        """
        ...
