"""인메모리 AccountRepository + Fake OAuth provider — DB/네트워크 없이 auth 테스트."""
import uuid

from src.features.auth.domain.models import AuthAccount, SocialProfile


class FakeAccountRepository:
    def __init__(self) -> None:
        self.by_cred: dict[tuple[str, str], AuthAccount] = {}

    async def find_by_credential(self, provider_cd: str, provider_user_id: str):
        return self.by_cred.get((provider_cd, provider_user_id))

    async def get_account(self, account_id):
        for acc in self.by_cred.values():
            if acc.id == account_id:
                return acc
        return None

    async def create_with_credential(self, profile: SocialProfile) -> AuthAccount:
        acc = AuthAccount(
            id=uuid.uuid4(),
            email=profile.email,
            display_name=profile.display_name,
            role_cd="READER",
        )
        self.by_cred[(profile.provider_cd, profile.provider_user_id)] = acc
        return acc


class FakeProvider:
    """고정 프로필을 돌려주는 OAuth provider 대역."""

    def __init__(self, provider_cd: str, profile: SocialProfile):
        self.provider_cd = provider_cd
        self._profile = profile

    def authorization_url(self, state: str) -> str:
        return f"https://fake/auth?state={state}"

    async def exchange(self, code: str) -> SocialProfile:
        return self._profile
