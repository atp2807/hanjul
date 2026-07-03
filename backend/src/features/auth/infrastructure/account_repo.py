"""AccountRepository 의 SQLAlchemy 구현."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.auth.domain.models import AuthAccount, SocialProfile
from src.infrastructure.db.models.account import Account, Credential


def _to_auth_account(acc: Account) -> AuthAccount:
    return AuthAccount(
        id=acc.id, email=acc.email, display_name=acc.display_name, role=acc.role, bio=acc.bio
    )


class SqlAccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_credential(self, provider_cd: str, provider_user_id: str) -> AuthAccount | None:
        stmt = (
            select(Account)
            .join(Credential, Credential.account_id == Account.id)
            .where(
                Credential.provider_cd == provider_cd,
                Credential.provider_user_id == provider_user_id,
            )
        )
        acc = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_auth_account(acc) if acc else None

    async def create_with_credential(self, profile: SocialProfile) -> AuthAccount:
        account = Account(
            email=profile.email,
            display_name=profile.display_name,
            role="READER",
        )
        self.session.add(account)
        await self.session.flush()
        self.session.add(
            Credential(
                account_id=account.id,
                provider_cd=profile.provider_cd,
                provider_user_id=profile.provider_user_id,
            )
        )
        await self.session.commit()
        return _to_auth_account(account)
