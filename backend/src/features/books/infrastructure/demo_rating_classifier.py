"""데모 콘텐츠 등급 분류기 — 외부호출 없는 키워드 휴리스틱 (dev/E2E, 결정적).

카테고리별로 tier 오름차순 한국어 키워드 리스트를 스캔해서, 매치되는 가장 높은 tier를
그 카테고리 등급으로 삼는다(매치 없으면 ALL). 같은 입력 → 같은 출력(결정적) — 테스트 검증.
실제 판단은 anthropic_rating_classifier(운영)가 담당하고, 이건 오프라인 대체물이다.
"""
from src.features.books.domain.content_rating import category_keys

# 카테고리 → {tier: [키워드]}. 낮은 tier부터, 높은 tier가 나중에 오버라이드.
_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "theme": {
        "AGE12": ["연애", "갈등", "이별"],
        "AGE15": ["죽음", "범죄", "불륜", "복수"],
        "AGE18": ["엽기", "반사회", "패륜"],
    },
    "violence": {
        "AGE12": ["몸싸움", "다툼", "주먹"],
        "AGE15": ["유혈", "상해", "칼부림", "폭행"],
        "AGE18": ["고문", "잔혹", "신체훼손", "학살"],
    },
    "sexual": {
        "AGE12": ["포옹", "손잡", "설렘"],
        "AGE15": ["키스", "노출", "스킨십"],
        "AGE18": ["정사", "성행위", "섹스", "음란"],
    },
    "language": {
        "AGE12": ["젠장", "제기랄"],
        "AGE15": ["욕설", "씨발", "새끼"],
        "AGE18": ["혐오표현", "패드립"],
    },
    "drug": {
        "AGE12": ["음주", "담배", "흡연"],
        "AGE15": ["만취", "약물"],
        "AGE18": ["마약", "필로폰", "대마"],
    },
    "gambling": {
        "AGE12": ["카드게임", "내기"],
        "AGE15": ["도박", "베팅", "카지노"],
        "AGE18": ["사행", "불법도박", "하우스"],
    },
    "imitation_risk": {
        "AGE12": ["장난", "위험한 놀이"],
        "AGE15": ["자해", "가출"],
        "AGE18": ["자살", "동반자살", "투신"],
    },
    "discrimination": {
        "AGE12": ["편견", "선입견"],
        "AGE15": ["차별", "비하"],
        "AGE18": ["혐오", "멸시", "조롱"],
    },
}


class DemoContentRatingClassifier:
    """키워드 스캔 기반 결정적 분류기 (외부 의존 없음)."""

    async def classify(self, text: str) -> dict[str, str]:
        haystack = text or ""
        result: dict[str, str] = {}
        for key in category_keys():
            tier = "ALL"
            # tier 오름차순으로 스캔 — 더 높은 tier 키워드가 있으면 승격.
            for candidate in ("AGE12", "AGE15", "AGE18"):
                words = _KEYWORDS.get(key, {}).get(candidate, [])
                if any(w in haystack for w in words):
                    tier = candidate
            result[key] = tier
        return result
