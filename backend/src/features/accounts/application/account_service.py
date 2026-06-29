"""accounts 서비스 — 유저 프로필 조회/수정 + 이름 디렉토리."""
from uuid import UUID

from src.features.accounts.domain.models import AccountNotFound, AccountProfile, AccountRepository


class AccountService:
    def __init__(self, repo: AccountRepository):
        self.repo = repo

    async def get_profile(self, account_id: UUID) -> AccountProfile:
        acc = await self.repo.get(account_id)
        if acc is None:
            raise AccountNotFound(account_id)
        return acc

    async def exists(self, account_id: UUID) -> bool:
        return await self.repo.exists(account_id)

    async def update_bio(self, account_id: UUID, bio: str | None) -> None:
        await self.repo.update_bio(account_id, bio)

    async def names_for(self, account_ids: list[UUID]) -> dict[UUID, str | None]:
        return await self.repo.names_for(account_ids)
