"""accounts 서비스 — 유저 프로필 조회/수정 + 이름 디렉토리 + 운영자 계정 조치."""
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

    # ── 연령 게이트(dc-daeb0d3d) ──────────────────────
    async def get_verified_tier(self, account_id: UUID) -> str:
        return await self.repo.get_verified_tier(account_id)

    async def set_verified_tier(self, account_id: UUID, tier: str) -> None:
        """potato 성인인증 승인 시 age_verification 피처가 호출 (AccountTierLookup 포트 구현)."""
        await self.repo.set_verified_tier(account_id, tier)

    # ── 운영자 계정 조치 ──────────────────────────────
    async def _require(self, account_id: UUID) -> None:
        if not await self.repo.exists(account_id):
            raise AccountNotFound(account_id)

    async def suspend(self, account_id: UUID) -> None:
        await self._require(account_id)
        await self.repo.set_status(account_id, "SUSPENDED")

    async def unsuspend(self, account_id: UUID) -> None:
        await self._require(account_id)
        await self.repo.set_status(account_id, "ACTIVE")

    async def withdraw(self, account_id: UUID) -> None:
        """회원탈퇴(익명화). 없는 계정이면 AccountNotFound."""
        if not await self.repo.withdraw(account_id):
            raise AccountNotFound(account_id)
