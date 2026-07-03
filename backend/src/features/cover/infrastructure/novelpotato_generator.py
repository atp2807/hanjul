"""AI 표지 생성 어댑터 — novelpotato 서비스 연동 + 데모 폴백.

novelpotato(별도 FastAPI 서비스)가 실제 생성 담당:
  POST {COVER_API_URL}  body {prompt, user_id, lora_id?}  → {image_url, title, description}
  (내부: GPT로 프롬프트 정제 → Stable Diffusion(sd.craftpotato.club). lora_id 로 캐릭터 일관성)
한줄은 그 계약을 HTTP 로 호출. 자격증명/엔드포인트 미설정 시 명시적 에러(503).

데모 생성기는 외부 의존 없이 결정적 placeholder(데이터 URI)를 돌려줘 dev/E2E 에서 동작.
"""
import html as _html
from urllib.parse import quote

import httpx


class NovelpotatoCoverGenerator:
    """라이브 — novelpotato /generate-cover 호출."""

    def __init__(self, api_url: str, api_key: str):
        self._api_url = api_url
        self._api_key = api_key

    async def generate(self, prompt: str, reference: str) -> str:
        if not self._api_url:
            raise RuntimeError("COVER_API_URL 미설정 — AI 표지 생성 비활성")
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(
                self._api_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"prompt": prompt, "user_id": reference, "lora_id": None},
            )
            res.raise_for_status()
            return res.json()["image_url"]


class DemoCoverGenerator:
    """데모 — 외부 호출 없이 프롬프트를 박은 SVG 데이터 URI 반환 (결정적·오프라인)."""

    async def generate(self, prompt: str, reference: str) -> str:
        label = _html.escape((prompt or "표지").strip()[:24], quote=True)
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='300' height='400'>"
            "<rect width='100%' height='100%' fill='#1f2937'/>"
            f"<text x='150' y='200' fill='#f9fafb' font-size='18' font-family='sans-serif' "
            f"text-anchor='middle'>{label}</text></svg>"
        )
        return "data:image/svg+xml;utf8," + quote(svg)


def build_cover_generator(settings):
    """COVER_DEMO 면 데모, 아니면 novelpotato 라이브."""
    if settings.COVER_DEMO:
        return DemoCoverGenerator()
    return NovelpotatoCoverGenerator(settings.COVER_API_URL, settings.COVER_API_KEY)
