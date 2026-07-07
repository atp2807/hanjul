"""회원탈퇴(익명화) + 개인정보 열람(export) E2E."""
import pytest
from sqlalchemy import select
from src.features.auth.domain.models import SocialProfile
from src.infrastructure.db.models.account import Account, Credential

from tests.integration.auth_helpers import login_token


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "bye-sub", "bye@x.com", "떠날사람")


async def test_export_then_withdraw_anonymizes(client, app_db):
    token, _ = await login_token(client, "google", "x")
    hdr = {"Authorization": f"Bearer {token}"}

    # 개인정보 열람(export)
    exp = await client.get("/api/me/export", headers=hdr)
    assert exp.status_code == 200, exp.text
    data = exp.json()
    assert data["account"]["email"] == "bye@x.com"
    assert data["account"]["displayName"] == "떠날사람"
    # 보유 개인정보 일괄 — 구매·판매정산·출금 (신규 유저 = 빈 값)
    assert data["purchases"] == []
    assert data["sales"]["totalOrders"] == 0
    assert data["bankAccount"] is None
    assert data["payouts"] == []

    # 탈퇴 (익명화)
    w = await client.delete("/api/me", headers=hdr)
    assert w.status_code == 204, w.text

    # DB: 계정 행은 남되 개인정보 제거 + DELETED, credential 삭제
    async with app_db() as s:
        accs = (await s.execute(select(Account))).scalars().all()
        assert len(accs) == 1  # 행 유지(법정 보존)
        acc = accs[0]
        assert acc.status == "DELETED"
        assert acc.email is None
        assert acc.display_name == "탈퇴한 사용자"
        assert acc.bio is None
        creds = (await s.execute(select(Credential))).scalars().all()
        assert creds == []  # 소셜 연결 삭제(재로그인 차단)


async def test_withdraw_requires_auth(client):
    assert (await client.delete("/api/me")).status_code == 401
    assert (await client.get("/api/me/export")).status_code == 401


async def test_relogin_after_withdraw_makes_new_account(client, app_db):
    """탈퇴 후 같은 소셜로 로그인하면 새 계정(익명화된 옛 계정과 분리)."""
    token, _ = await login_token(client, "google", "x")
    await client.delete("/api/me", headers={"Authorization": f"Bearer {token}"})

    # 같은 소셜 재로그인 → credential 없으므로 새 계정 생성
    token2, is_new = await login_token(client, "google", "y")
    me = await client.get("/api/me", headers={"Authorization": f"Bearer {token2}"})
    assert me.status_code == 200
    assert me.json()["email"] == "bye@x.com"  # 새 계정, 정상 프로필
    async with app_db() as s:
        accs = (await s.execute(select(Account))).scalars().all()
        assert len(accs) == 2  # 익명화된 옛 계정 + 새 계정
