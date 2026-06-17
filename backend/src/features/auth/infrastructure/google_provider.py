"""Google OAuth 어댑터 (OIDC). 나라별 provider 의 첫 구현체.

주의: 실제 토큰 교환은 Google 자격증명(client id/secret)이 있어야 동작 — 라이브 검증은
운영 환경에서. 구조/플로우는 provider 포트 계약을 따른다.
"""
from urllib.parse import urlencode

import httpx

from src.features.auth.domain.models import SocialProfile

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthProvider:
    provider_cd = "GOOGLE"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange(self, code: str) -> SocialProfile:
        async with httpx.AsyncClient(timeout=10) as client:
            token_res = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            info_res = await client.get(
                _USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            info_res.raise_for_status()
            info = info_res.json()

        return SocialProfile(
            provider_cd=self.provider_cd,
            provider_user_id=info["sub"],
            email=info.get("email"),
            display_name=info.get("name"),
        )
