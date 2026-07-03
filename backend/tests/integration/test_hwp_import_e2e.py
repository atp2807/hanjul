"""HWP 가져오기 엔드포인트 E2E — POST /api/import/hwp-parse (상태없는 파싱)."""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import get_auth_service, token_issuer  # noqa: E402
from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.fixtures.hwpx_fixture import build_hwpx  # noqa: E402
from tests.integration.auth_helpers import login_token  # noqa: E402

USER = SocialProfile("GOOGLE", "hwp-u", "u@x.com", "작가")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", USER)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_requires_login(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/import/hwp-parse",
            files={"file": ("m.hwpx", build_hwpx(["안녕"]), "application/octet-stream")},
        )
        assert r.status_code == 401


async def test_invalid_file_returns_422(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_token(c, "google", "u")
        auth = {"Authorization": f"Bearer {token}"}
        r = await c.post(
            "/api/import/hwp-parse",
            files={"file": ("notes.txt", b"this is plain text, not hwp", "text/plain")},
            headers=auth,
        )
        assert r.status_code == 422
        assert "HWP" in r.json()["detail"]


async def test_valid_hwpx_returns_blocks(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_token(c, "google", "u")
        auth = {"Authorization": f"Bearer {token}"}
        data = build_hwpx(["제목 같은 첫 줄", "본문 문단"])
        r = await c.post(
            "/api/import/hwp-parse",
            files={"file": ("manuscript.hwpx", data, "application/octet-stream")},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        assert r.json() == {
            "blocks": [
                {"type": "p", "spans": [{"text": "제목 같은 첫 줄", "marks": []}]},
                {"type": "p", "spans": [{"text": "본문 문단", "marks": []}]},
            ]
        }
