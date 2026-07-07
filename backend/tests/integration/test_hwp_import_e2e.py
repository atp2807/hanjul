"""HWP/HWPX 가져오기 E2E — 상태 없는 파싱 엔드포인트(로그인만, book 무관).

미로그인 401 · 손상파일 422(PDF 변환 안내 문구 검증 = 이번 설계 핵심) · 정상 HWPX 200 + 블록.
"""
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
from tests.fixtures.hwpx_builder import build_hwpx  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

AUTHOR = SocialProfile("GOOGLE", "hwp-a", "a@x.com", "작가")


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", AUTHOR)},
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
            files={"file": ("m.hwpx", build_hwpx(["가"]), "application/hwp+zip")},
        )
        assert r.status_code == 401


async def test_corrupt_file_returns_422_with_pdf_hint(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "a")
        r = await c.post(
            "/api/import/hwp-parse",
            files={"file": ("broken.hwpx", b"not a hwpx", "application/hwp+zip")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422, r.text
        assert "PDF로 변환" in r.json()["detail"]


async def test_valid_hwpx_returns_blocks(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "a")
        r = await c.post(
            "/api/import/hwp-parse",
            files={"file": ("manuscript.hwpx", build_hwpx(["첫 문단입니다", "둘째 문단입니다", "셋째"]), "application/hwp+zip")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        assert r.json() == {
            "blocks": [
                {"type": "p", "spans": [{"text": "첫 문단입니다", "marks": []}]},
                {"type": "p", "spans": [{"text": "둘째 문단입니다", "marks": []}]},
                {"type": "p", "spans": [{"text": "셋째", "marks": []}]},
            ]
        }
