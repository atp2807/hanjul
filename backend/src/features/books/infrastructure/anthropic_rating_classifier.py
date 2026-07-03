"""실 콘텐츠 등급 분류기 — Anthropic Messages API 직접 호출 (순수 httpx).

프로젝트에 anthropic SDK 의존성이 없어 toss_client 스타일로 httpx POST를 직접 쓴다.
시스템 프롬프트에 content_rating_criteria.json의 8기준+등급별 가이드를 그대로 싣고,
tool-use(forced tool_choice)로 8개 카테고리 각각을 4단계 중 하나로 반환하도록 강제한다.

응답 파싱 시 알 수 없는 카테고리 key/등급값이 오면 조용히 기본값을 넣지 않고 명확한 예외로
실패시킨다(잘못된 결과를 신뢰하지 않기 위함). API 키 미설정은 생성이 아니라 **호출 시점**에
plain RuntimeError로 던진다 — 표현층이 반드시 except RuntimeError → HTTPException(503)로 잡는다.
"""
import httpx

from src.features.books.domain.content_rating import (
    TIERS,
    category_keys,
    is_valid_tier,
    load_criteria,
)

_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-opus-4-8"
_TOOL_NAME = "set_content_rating"
_MAX_TOKENS = 1024
_TIMEOUT = 60.0


def _build_system_prompt() -> str:
    """criteria JSON의 8기준+등급별 가이드를 그대로 프롬프트에 싣는다."""
    criteria = load_criteria()
    labels = criteria["tierLabels"]
    lines = [
        "당신은 한국 웹소설·웹툰의 콘텐츠 연령등급을 매기는 심의자입니다.",
        "플랫폼 자율등급 기준(한국만화영상진흥원 틀 참고)에 따라 아래 8개 기준 각각을",
        "4단계(ALL·AGE12·AGE15·AGE18) 중 하나로 분류하세요. 최종등급은 8개 중 최댓값입니다.",
        "",
        f"등급 라벨: {', '.join(f'{k}={v}' for k, v in labels.items())}",
        "",
        "기준별 가이드:",
    ]
    for cat in criteria["categories"]:
        lines.append(f"[{cat['key']}] {cat['label']}")
        for tier in TIERS:
            guide = cat["guide"].get(tier, "")
            lines.append(f"  - {tier}: {guide}")
    lines.append("")
    lines.append(f"반드시 {_TOOL_NAME} 도구를 호출해 8개 기준 모두에 등급을 부여하세요.")
    return "\n".join(lines)


def _tool_schema() -> dict:
    props = {key: {"type": "string", "enum": list(TIERS)} for key in category_keys()}
    return {
        "name": _TOOL_NAME,
        "description": "8개 콘텐츠 기준 각각에 연령등급(ALL/AGE12/AGE15/AGE18)을 부여한다.",
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": category_keys(),
        },
    }


class AnthropicContentRatingClassifier:
    """라이브 — Anthropic Messages API 호출."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def classify(self, text: str) -> dict[str, str]:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 미설정 — 콘텐츠 등급 자동분류 비활성")
        body = {
            "model": _MODEL,
            "max_tokens": _MAX_TOKENS,
            "system": _build_system_prompt(),
            "messages": [
                {
                    "role": "user",
                    "content": f"다음 본문의 연령등급을 8기준으로 분류하세요:\n\n{text}",
                }
            ],
            "tools": [_tool_schema()],
            "tool_choice": {"type": "tool", "name": _TOOL_NAME},
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            res = await client.post(
                _URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            )
        if res.status_code != 200:
            raise RuntimeError(f"Anthropic 등급 분류 실패 (HTTP {res.status_code})")
        data = res.json()
        return _parse(data)


def _parse(data: dict) -> dict[str, str]:
    """tool_use 블록에서 8기준 등급을 꺼내고 엄격 검증. 이상값은 예외로 실패."""
    blocks = data.get("content") or []
    tool_input = next(
        (b.get("input") for b in blocks if b.get("type") == "tool_use" and b.get("name") == _TOOL_NAME),
        None,
    )
    if not isinstance(tool_input, dict):
        raise RuntimeError("Anthropic 응답에 등급 분류 결과(tool_use)가 없어요.")
    expected = set(category_keys())
    got = set(tool_input.keys())
    if got != expected:
        raise RuntimeError(f"등급 분류 카테고리 불일치: 누락={expected - got} 초과={got - expected}")
    result: dict[str, str] = {}
    for key, tier in tool_input.items():
        if not is_valid_tier(tier):
            raise RuntimeError(f"알 수 없는 등급값 '{tier}' (카테고리 {key})")
        result[key] = tier
    return result


def build_rating_classifier(settings):
    """CONTENT_RATING_AI_DEMO면 데모, 아니면 Anthropic 라이브."""
    if settings.CONTENT_RATING_AI_DEMO:
        from src.features.books.infrastructure.demo_rating_classifier import (
            DemoContentRatingClassifier,
        )

        return DemoContentRatingClassifier()
    return AnthropicContentRatingClassifier(settings.ANTHROPIC_API_KEY)
