"""AccountRepository(accounts) 의 SQLAlchemy 구현 — usr.account 프로필/디렉토리."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.accounts.domain.models import AccountProfile
from src.infrastructure.db.models.account import Account


def _to_profile(acc: Account) -> AccountProfile:
    return AccountProfile(
        id=acc.id, email=acc.email, display_name=acc.display_name, role_cd=acc.role_cd, bio=acc.bio
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

    async def names_for(self, account_ids: list[UUID]) -> dict[UUID, str | None]:
        if not account_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Account.id, Account.display_name).where(Account.id.in_(account_ids))
            )
        ).all()
        return {aid: name for aid, name in rows}
