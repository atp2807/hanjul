"""OAuth provider 포트 — 나라별 소셜(Google/Naver/Kakao/LINE…)을 같은 계약으로.

새 나라 provider 추가 = 이 Protocol 을 구현하는 어댑터 1개 + AUTH_PROVIDERS 에 코드 추가.
스키마/서비스 변경 0.
"""
from typing import Protocol

from src.features.auth.domain.models import SocialProfile


class OAuthProvider(Protocol):
    provider_cd: str

    def authorization_url(self, state: str) -> str:
        """소셜 로그인 페이지로 보낼 URL."""
        ...

    async def exchange(self, code: str) -> SocialProfile:
        """callback 의 code → access token → 사용자 프로필(정규화)."""
        ...
