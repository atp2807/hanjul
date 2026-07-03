"""auth 서비스 — 소셜 로그인 오케스트레이션 (provider 무관)."""
from src.features.auth.application.token import JwtTokenIssuer
from src.features.auth.domain.models import AuthResult, SocialProfile, UnknownProvider
from src.features.auth.domain.provider import OAuthProvider
from src.features.auth.domain.repository import AccountRepository


class AuthService:
    def __init__(
        self,
        repo: AccountRepository,
        providers: dict[str, OAuthProvider],
        token_issuer: JwtTokenIssuer,
    ):
        self.repo = repo
        self.providers = providers
        self.token_issuer = token_issuer

    def _provider(self, provider_cd: str) -> OAuthProvider:
        provider = self.providers.get(provider_cd.upper())
        if provider is None:
            raise UnknownProvider(provider_cd)
        return provider

    def login_url(self, provider_cd: str, state: str) -> str:
        return self._provider(provider_cd).authorization_url(state)

    async def complete_login(self, provider_cd: str, code: str) -> AuthResult:
        """callback 처리: code → 프로필 → account(find-or-create) → JWT."""
        provider = self._provider(provider_cd)
        profile = await provider.exchange(code)

        account = await self.repo.find_by_credential(profile.provider_cd, profile.provider_user_id)
        is_new = account is None
        if account is None:
            account = await self.repo.create_with_credential(profile)

        token = self.token_issuer.issue(account.id, account.role)
        return AuthResult(account=account, token=token, is_new=is_new)

    async def login_with_profile(self, profile: SocialProfile) -> AuthResult:
        """OAuth 교환 없이 프로필로 바로 find-or-create + JWT.

        E2E/로컬 전용. 호출 엔드포인트가 플래그로 게이트해야 한다(운영 차단).
        """
        account = await self.repo.find_by_credential(profile.provider_cd, profile.provider_user_id)
        is_new = account is None
        if account is None:
            account = await self.repo.create_with_credential(profile)
        token = self.token_issuer.issue(account.id, account.role)
        return AuthResult(account=account, token=token, is_new=is_new)
