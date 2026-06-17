"""SqlAccountRepository 통합 — 실 DB(SQLite)에 소셜 신원 영속."""
from src.features.auth.domain.models import SocialProfile
from src.features.auth.infrastructure.account_repo import SqlAccountRepository

PROFILE = SocialProfile("GOOGLE", "sub-xyz", "u@x.com", "유저")


async def test_create_then_find_by_credential(sessionmaker):
    async with sessionmaker() as s:
        created = await SqlAccountRepository(s).create_with_credential(PROFILE)

    async with sessionmaker() as s2:
        found = await SqlAccountRepository(s2).find_by_credential("GOOGLE", "sub-xyz")

    assert found is not None
    assert found.id == created.id
    assert found.email == "u@x.com"
    assert found.display_name == "유저"


async def test_find_missing_returns_none(sessionmaker):
    async with sessionmaker() as s:
        assert await SqlAccountRepository(s).find_by_credential("GOOGLE", "nope") is None
