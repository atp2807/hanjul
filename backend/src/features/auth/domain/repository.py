"""account 리포지토리 포트."""
from typing import Protocol
from uuid import UUID

from src.features.auth.domain.models import AuthAccount, SocialProfile


class AccountRepository(Protocol):
    async def find_by_credential(self, provider_cd: str, provider_user_id: str) -> AuthAccount | None:
        ...

    async def create_with_credential(self, profile: SocialProfile) -> AuthAccount:
        """소셜 프로필로 account + credential 을 함께 생성."""
        ...

