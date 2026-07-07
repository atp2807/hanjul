"""AccountService 단위 — 프로필 조회/수정 + 운영자 계정 조치 (Fake repo)."""
import uuid

import pytest
from src.features.accounts.application.account_service import AccountService
from src.features.accounts.domain.models import AccountNotFound, AccountProfile

from tests.fixtures.fake_accounts_repo import FakeAccountsRepository


def _profile(**overrides) -> AccountProfile:
    defaults = dict(
        id=uuid.uuid4(), email="a@b.com", display_name="작가A", role="AUTHOR",
        bio="소개", status="ACTIVE",
    )
    defaults.update(overrides)
    return AccountProfile(**defaults)


# ── 조회 ──────────────────────────────────────────────
async def test_get_profile_returns_profile_when_found():
    repo = FakeAccountsRepository()
    profile = _profile()
    repo.seed(profile)
    svc = AccountService(repo)

    result = await svc.get_profile(profile.id)

    assert result is profile


async def test_get_profile_raises_not_found_when_missing():
    svc = AccountService(FakeAccountsRepository())
    with pytest.raises(AccountNotFound):
        await svc.get_profile(uuid.uuid4())


async def test_exists_true_for_seeded_account():
    repo = FakeAccountsRepository()
    profile = _profile()
    repo.seed(profile)
    assert await AccountService(repo).exists(profile.id) is True


async def test_exists_false_for_missing_account():
    assert await AccountService(FakeAccountsRepository()).exists(uuid.uuid4()) is False


# ── 프로필 수정 ───────────────────────────────────────
async def test_update_bio_normalizes_blank_to_none():
    repo = FakeAccountsRepository()
    profile = _profile()
    repo.seed(profile)
    svc = AccountService(repo)

    await svc.update_bio(profile.id, "   ")

    assert repo.accounts[profile.id].bio is None


async def test_names_for_returns_directory_for_known_ids_only():
    repo = FakeAccountsRepository()
    p1, p2 = _profile(display_name="철수"), _profile(display_name="영희")
    repo.seed(p1)
    repo.seed(p2)
    svc = AccountService(repo)

    names = await svc.names_for([p1.id, p2.id, uuid.uuid4()])

    assert names == {p1.id: "철수", p2.id: "영희"}


# ── 운영자 계정 조치 ──────────────────────────────────
async def test_suspend_sets_status_suspended():
    repo = FakeAccountsRepository()
    profile = _profile()
    repo.seed(profile)
    svc = AccountService(repo)

    await svc.suspend(profile.id)

    assert repo.accounts[profile.id].status == "SUSPENDED"


async def test_suspend_missing_account_raises_not_found():
    svc = AccountService(FakeAccountsRepository())
    with pytest.raises(AccountNotFound):
        await svc.suspend(uuid.uuid4())


async def test_unsuspend_restores_active_status():
    repo = FakeAccountsRepository()
    profile = _profile(status="SUSPENDED")
    repo.seed(profile)
    svc = AccountService(repo)

    await svc.unsuspend(profile.id)

    assert repo.accounts[profile.id].status == "ACTIVE"


async def test_unsuspend_missing_account_raises_not_found():
    svc = AccountService(FakeAccountsRepository())
    with pytest.raises(AccountNotFound):
        await svc.unsuspend(uuid.uuid4())


# ── 회원탈퇴 ──────────────────────────────────────────
async def test_withdraw_anonymizes_and_marks_deleted():
    repo = FakeAccountsRepository()
    profile = _profile()
    repo.seed(profile)
    svc = AccountService(repo)

    await svc.withdraw(profile.id)

    acc = repo.accounts[profile.id]
    assert acc.email is None
    assert acc.display_name == "탈퇴한 사용자"
    assert acc.bio is None
    assert acc.status == "DELETED"


async def test_withdraw_missing_account_raises_not_found():
    svc = AccountService(FakeAccountsRepository())
    with pytest.raises(AccountNotFound):
        await svc.withdraw(uuid.uuid4())
