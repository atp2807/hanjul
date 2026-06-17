"""활성 OAuth provider 레지스트리 — 설정(AUTH_PROVIDERS)에서 조립.

나라별 provider 추가 위치: 여기에 코드 분기 하나 + 어댑터 import 만 추가.
"""
from src.config.settings import Settings
from src.features.auth.domain.provider import OAuthProvider
from src.features.auth.infrastructure.google_provider import GoogleOAuthProvider


def build_providers(settings: Settings) -> dict[str, OAuthProvider]:
    registry: dict[str, OAuthProvider] = {}
    for code in settings.auth_provider_list:
        if code == "GOOGLE":
            registry["GOOGLE"] = GoogleOAuthProvider(
                settings.GOOGLE_CLIENT_ID,
                settings.GOOGLE_CLIENT_SECRET,
                settings.GOOGLE_REDIRECT_URI,
            )
        # elif code == "NAVER": registry["NAVER"] = NaverOAuthProvider(...)
        # elif code == "KAKAO": registry["KAKAO"] = KakaoOAuthProvider(...)
        # elif code == "LINE":  registry["LINE"]  = LineOAuthProvider(...)
    return registry
