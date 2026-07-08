"""AccountRepository(accounts) 의 SQLAlchemy 구현 — usr.account 프로필/디렉토리."""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.accounts.domain.models import AccountProfile
from src.infrastructure.db.models.account import Account, Credential

WITHDRAWN_NAME = "탈퇴한 사용자"


def _to_profile(acc: Account) -> AccountProfile:
    return AccountProfile(
        id=acc.id,
        email=acc.email,
        display_name=acc.display_name,
        role=acc.role,
        bio=acc.bio,
        status=acc.status,
        verified_tier=acc.verified_tier,
    )


class SqlAccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, account_id: UUID) -> AccountProfile | None:
        acc = await self.session.get(Account, account_id)
        return _to_profile(acc) if acc else None

    async def exists(self, account_id: UUID) -> bool:
        return await self.session.get(Account, account_id) is not None

    async def update_bio(self, account_id: UUID, bio: str | None) -> None:
        acc = await self.session.get(Account, account_id)
        if acc is not None:
            acc.bio = (bio or "").strip() or None
            await self.session.commit()

    async def set_status(self, account_id: UUID, status: str) -> None:
        acc = await self.session.get(Account, account_id)
        if acc is not None:
            acc.status = status
            await self.session.commit()

    async def get_verified_tier(self, account_id: UUID) -> str:
        acc = await self.session.get(Account, account_id)
        return acc.verified_tier if acc is not None else "ALL"

    async def set_verified_tier(self, account_id: UUID, tier: str) -> None:
        acc = await self.session.get(Account, account_id)
        if acc is not None:
            acc.verified_tier = tier
            await self.session.commit()

    async def withdraw(self, account_id: UUID) -> bool:
        acc = await self.session.get(Account, account_id)
        if acc is None:
            return False
        # 개인정보 익명화 (계정 행은 유지 — 주문/정산 RESTRICT 법정보존)
        acc.email = None
        acc.display_name = WITHDRAWN_NAME
        acc.bio = None
        acc.status = "DELETED"
        # 소셜 연결 삭제 → 재로그인 시 이 계정으로 못 돌아옴(새 계정 생성)
        await self.session.execute(delete(Credential).where(Credential.account_id == account_id))
        await self.session.commit()
        return True

    async def names_for(self, account_ids: list[UUID]) -> dict[UUID, str | None]:
        if not account_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Account.id, Account.display_name).where(Account.id.in_(account_ids))
            )
        ).all()
        return {aid: name for aid, name in rows}
