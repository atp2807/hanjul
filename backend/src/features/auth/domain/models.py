"""auth 도메인 — 소셜 프로필 값객체 + 에러."""
from dataclasses import dataclass
from uuid import UUID

from src.shared.errors import DomainError


@dataclass(frozen=True)
class SocialProfile:
    """provider 가 돌려주는 정규화된 사용자 신원."""
    provider_cd: str           # GOOGLE | NAVER | ...
    provider_user_id: str      # provider 의 안정적 식별자(sub)
    email: str | None = None
    display_name: str | None = None


@dataclass
class AuthAccount:
    id: UUID
    email: str | None
    display_name: str | None
    role: str
    bio: str | None = None


@dataclass(frozen=True)
class AccountPrincipal:
    """JWT 클레임에서 복원한 인증 주체 (DB 조회 없이 authz/entitlement용)."""
    id: UUID
    role: str


@dataclass
class AuthResult:
    account: AuthAccount
    token: str
    is_new: bool


class UnknownProvider(DomainError):
    """지원하지 않거나 비활성화된 소셜 제공자 (400). 표현층 매핑 없이 중앙 핸들러가 처리."""
    status_code = 400

    def __init__(self, provider_cd: str):
        self.provider_cd = provider_cd
        super().__init__("지원하지 않는 로그인 방식이에요.")


class OAuthExchangeError(Exception):
    """소셜 토큰 교환/조회 실패 — redirect_uri_mismatch, invalid_grant(코드 재사용) 등.

    ⚠️ DomainError 아님 — HTTP 에러 응답이 아니라 표현층이 프론트로 안내 리다이렉트(#error=)로
    변환하는 특수 예외. detail 에 provider가 준 에러 원문을 담아 로그로 디버깅(첫 실연동 시 필수).
    """
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
