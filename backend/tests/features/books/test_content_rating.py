"""콘텐츠 등급 도메인 + 데모 분류기 단위테스트."""
import pytest
from src.features.books.domain.content_rating import (
    TIERS,
    AgeVerificationRequired,
    category_keys,
    is_book_accessible,
    is_valid_category,
    is_valid_tier,
    max_tier,
    overall_rating,
    tier_rank,
)
from src.features.books.infrastructure.demo_rating_classifier import (
    DemoContentRatingClassifier,
)
from src.shared.errors import ForbiddenError


def test_tier_rank_is_ordinal():
    assert tier_rank("ALL") < tier_rank("AGE12") < tier_rank("AGE15") < tier_rank("AGE18")


def test_tier_rank_unknown_raises():
    with pytest.raises(ValueError):
        tier_rank("AGE7")


def test_max_tier_picks_strictest():
    assert max_tier(["ALL", "AGE15", "AGE12"]) == "AGE15"
    assert max_tier(["AGE18", "ALL"]) == "AGE18"
    assert max_tier([]) == "ALL"  # 비어 있으면 ALL


def test_overall_rating_is_max_of_detail():
    detail = {k: "ALL" for k in category_keys()}
    detail["violence"] = "AGE15"
    detail["sexual"] = "AGE18"
    assert overall_rating(detail) == "AGE18"


def test_overall_rating_all_when_all_all():
    assert overall_rating({k: "ALL" for k in category_keys()}) == "ALL"


def test_validity_helpers():
    assert is_valid_tier("AGE15") and not is_valid_tier("AGE7")
    assert is_valid_category("violence") and not is_valid_category("nope")
    assert len(category_keys()) == 8
    assert set(TIERS) == {"ALL", "AGE12", "AGE15", "AGE18"}


async def test_demo_classifier_is_deterministic():
    clf = DemoContentRatingClassifier()
    text = "칼부림과 유혈이 낭자하고 마약을 하는 장면"
    first = await clf.classify(text)
    second = await clf.classify(text)
    assert first == second  # 같은 입력 → 같은 출력
    assert set(first.keys()) == set(category_keys())  # 8기준 전부
    assert first["violence"] == "AGE15"  # 유혈·칼부림
    assert first["drug"] == "AGE18"  # 마약


async def test_demo_classifier_no_match_is_all():
    result = await DemoContentRatingClassifier().classify("잔잔한 봄날의 산책과 우정 이야기")
    assert all(tier == "ALL" for tier in result.values())


async def test_demo_classifier_escalates_to_highest_matched_tier():
    # AGE15(유혈) + AGE18(고문) 키워드 동시 → 더 높은 AGE18
    result = await DemoContentRatingClassifier().classify("유혈이 있고 고문 장면도 있다")
    assert result["violence"] == "AGE18"


# ── 연령 게이트(dc-daeb0d3d) — 책 등급 vs 계정 인증등급 ──────────
@pytest.mark.parametrize(
    ("book_rating", "account_tier", "expected"),
    [
        # ALL 책 — 누구나 접근 가능
        ("ALL", "ALL", True),
        ("ALL", "AGE12", True),
        ("ALL", "AGE15", True),
        ("ALL", "AGE18", True),
        # AGE12 책 — ALL 계정만 차단
        ("AGE12", "ALL", False),
        ("AGE12", "AGE12", True),
        ("AGE12", "AGE15", True),
        ("AGE12", "AGE18", True),
        # AGE15 책
        ("AGE15", "ALL", False),
        ("AGE15", "AGE12", False),
        ("AGE15", "AGE15", True),
        ("AGE15", "AGE18", True),
        # AGE18 책 — AGE18 계정만 통과
        ("AGE18", "ALL", False),
        ("AGE18", "AGE12", False),
        ("AGE18", "AGE15", False),
        ("AGE18", "AGE18", True),
    ],
)
def test_is_book_accessible_matrix(book_rating, account_tier, expected):
    assert is_book_accessible(book_rating, account_tier) is expected


def test_age_verification_required_is_forbidden_403():
    exc = AgeVerificationRequired()
    assert isinstance(exc, ForbiddenError)
    assert exc.status_code == 403
