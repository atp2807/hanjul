"""회원탈퇴(익명화) + 개인정보 열람(export) E2E."""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from src.infrastructure.db.models.account import Account, Credential  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_token  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "bye-sub", "bye@x.com", "떠날사람")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", PROFILE)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield sessionmaker
    app.dependency_overrides.clear()


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_export_then_withdraw_anonymizes(app_db):
    async with _client() as c:
        token, _ = await login_token(c, "google", "x")
        hdr = {"Authorization": f"Bearer {token}"}

        # 개인정보 열람(export)
        exp = await c.get("/api/me/export", headers=hdr)
        assert exp.status_code == 200, exp.text
        data = exp.json()
        assert data["account"]["email"] == "bye@x.com"
        assert data["account"]["displayName"] == "떠날사람"

        # 탈퇴 (익명화)
        w = await c.delete("/api/me", headers=hdr)
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


async def test_withdraw_requires_auth(app_db):
    async with _client() as c:
        assert (await c.delete("/api/me")).status_code == 401
        assert (await c.get("/api/me/export")).status_code == 401


async def test_relogin_after_withdraw_makes_new_account(app_db):
    """탈퇴 후 같은 소셜로 로그인하면 새 계정(익명화된 옛 계정과 분리)."""
    async with _client() as c:
        token, _ = await login_token(c, "google", "x")
        await c.delete("/api/me", headers={"Authorization": f"Bearer {token}"})

        # 같은 소셜 재로그인 → credential 없으므로 새 계정 생성
        token2, is_new = await login_token(c, "google", "y")
        me = await c.get("/api/me", headers={"Authorization": f"Bearer {token2}"})
        assert me.status_code == 200
        assert me.json()["email"] == "bye@x.com"  # 새 계정, 정상 프로필
        async with app_db() as s:
            accs = (await s.execute(select(Account))).scalars().all()
            assert len(accs) == 2  # 익명화된 옛 계정 + 새 계정
