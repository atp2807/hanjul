"""novelpotato AI 표지 생성 어댑터 (웹소설 표지 생성 자산 연동).

주의: 라이브 생성은 이미지 API 자격증명(COVER_API_URL/KEY) 필요 → 운영.
구조/플로우는 CoverGenerator 계약. 미설정 시 호출하면 명시적 에러.
"""
import httpx


class NovelpotatoCoverGenerator:
    def __init__(self, api_url: str, api_key: str):
        self._api_url = api_url
        self._api_key = api_key

    async def generate(self, prompt: str) -> str:
        if not self._api_url:
            raise RuntimeError("COVER_API_URL 미설정 — AI 표지 생성 비활성")
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                self._api_url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"prompt": prompt},
            )
            res.raise_for_status()
            return res.json()["image_url"]
