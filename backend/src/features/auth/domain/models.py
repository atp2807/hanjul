"""auth 도메인 — 소셜 프로필 값객체 + 에러."""
from dataclasses import dataclass
from uuid import UUID


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
    role_cd: str
    bio: str | None = None


@dataclass(frozen=True)
class AccountPrincipal:
    """JWT 클레임에서 복원한 인증 주체 (DB 조회 없이 authz/entitlement용)."""
    id: UUID
    role_cd: str


@dataclass
class AuthResult:
    account: AuthAccount
    token: str
    is_new: bool


class UnknownProvider(Exception):
    def __init__(self, provider_cd: str):
        self.provider_cd = provider_cd
        super().__init__(f"unknown or disabled provider: {provider_cd}")
