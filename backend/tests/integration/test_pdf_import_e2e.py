"""PDF 가져오기 엔드포인트 E2E — 인증 게이트 + 실제 파싱(상태 없음, DB 저장 없음)."""
import fitz
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
from tests.integration.auth_helpers import login_account  # noqa: E402

PROFILE = SocialProfile("GOOGLE", "pdf-x", "pdf@x.com", "작가")


def _sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Big Title", fontsize=24, fontname="helv")
    page.insert_text((72, 140), "First body line here", fontsize=11, fontname="helv")
    page.insert_text((72, 180), "Second body line here", fontsize=11, fontname="helv")
    return doc.tobytes()


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session),
            {"GOOGLE": FakeProvider("GOOGLE", PROFILE)},
            token_issuer(),
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_unauthenticated_returns_401(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/import/pdf-parse",
            files={"file": ("m.pdf", _sample_pdf(), "application/pdf")},
        )
        assert r.status_code == 401


async def test_corrupt_pdf_returns_422(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        r = await c.post(
            "/api/import/pdf-parse",
            files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422, r.text


async def test_valid_pdf_returns_blocks(app_db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        r = await c.post(
            "/api/import/pdf-parse",
            files={"file": ("m.pdf", _sample_pdf(), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        blocks = r.json()["blocks"]
        by_text = {b["spans"][0]["text"]: b for b in blocks}
        assert by_text["Big Title"]["type"] == "h1"
        assert by_text["First body line here"]["type"] == "p"
