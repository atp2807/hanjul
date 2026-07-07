"""인메모리 AccountRepository(accounts 피처) — 서비스 단위 테스트용.

⚠️ auth 피처의 기존 FakeAccountRepository(단수, fake_account_repo.py)와 이름이
겹쳐 이 파일은 복수형(accounts)으로 분리 — CLAUDE.md W2 컨벤션.
Protocol 구현 대상: src.features.accounts.domain.models.AccountRepository
  (get · exists · update_bio · names_for · set_status · withdraw)
"""
from uuid import UUID

from src.features.accounts.domain.models import AccountProfile

WITHDRAWN_NAME = "탈퇴한 사용자"


# ── Fake 리포지토리 ──────────────────────────────────
class FakeAccountsRepository:
    def __init__(self) -> None:
        self.accounts: dict[UUID, AccountProfile] = {}

    def seed(self, profile: AccountProfile) -> None:
        """테스트 준비용 — 계정 프로필을 직접 채워넣는다."""
        self.accounts[profile.id] = profile

    async def get(self, account_id: UUID) -> AccountProfile | None:
        return self.accounts.get(account_id)

    async def exists(self, account_id: UUID) -> bool:
        return account_id in self.accounts

    async def update_bio(self, account_id: UUID, bio: str | None) -> None:
        acc = self.accounts.get(account_id)
        if acc is not None:
            acc.bio = (bio or "").strip() or None

    async def names_for(self, account_ids: list[UUID]) -> dict[UUID, str | None]:
        return {aid: self.accounts[aid].display_name for aid in account_ids if aid in self.accounts}

    async def set_status(self, account_id: UUID, status: str) -> None:
        acc = self.accounts.get(account_id)
        if acc is not None:
            acc.status = status

    async def withdraw(self, account_id: UUID) -> bool:
        acc = self.accounts.get(account_id)
        if acc is None:
            return False
        acc.email = None
        acc.display_name = WITHDRAWN_NAME
        acc.bio = None
        acc.status = "DELETED"
        return True
