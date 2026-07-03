"""AuthService — 소셜 로그인 find-or-create 로직 (Fake provider/repo)."""
import pytest

from src.features.auth.application.auth_service import AuthService
from src.features.auth.application.token import JwtTokenIssuer
from src.features.auth.domain.models import SocialProfile, UnknownProvider
from tests.fixtures.fake_account_repo import FakeAccountRepository, FakeProvider

PROFILE = SocialProfile("GOOGLE", "sub-123", "a@b.com", "박작가")


def make_service(profile=PROFILE):
    repo = FakeAccountRepository()
    providers = {"GOOGLE": FakeProvider("GOOGLE", profile)}
    issuer = JwtTokenIssuer("secret", "HS256", 1)
    return AuthService(repo, providers, issuer), issuer


async def test_first_login_creates_account_and_token():
    svc, issuer = make_service()
    res = await svc.complete_login("google", "code")  # provider 코드 대소문자 무관
    assert res.is_new is True
    assert res.account.email == "a@b.com"
    assert res.account.role == "READER"
    payload = issuer.verify(res.token)
    assert payload["sub"] == str(res.account.id)


async def test_returning_login_reuses_account():
    svc, _ = make_service()
    first = await svc.complete_login("google", "c1")
    second = await svc.complete_login("google", "c2")
    assert second.is_new is False
    assert second.account.id == first.account.id


async def test_unknown_provider_raises():
    svc, _ = make_service()
    with pytest.raises(UnknownProvider):
        await svc.complete_login("naver", "code")


def test_login_url_delegates_to_provider():
    svc, _ = make_service()
    assert "state=xyz" in svc.login_url("google", "xyz")
