"""PDF 가져오기 엔드포인트 E2E — 인증 게이트 + 실제 파싱(상태 없음, DB 저장 없음)."""
import fitz
import pytest
from src.features.auth.domain.models import SocialProfile

from tests.integration.auth_helpers import login_account


def _sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Big Title", fontsize=24, fontname="helv")
    page.insert_text((72, 140), "First body line here", fontsize=11, fontname="helv")
    page.insert_text((72, 180), "Second body line here", fontsize=11, fontname="helv")
    return doc.tobytes()


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "pdf-x", "pdf@x.com", "작가")


async def test_unauthenticated_returns_401(client):
    r = await client.post(
        "/api/import/pdf-parse",
        files={"file": ("m.pdf", _sample_pdf(), "application/pdf")},
    )
    assert r.status_code == 401


async def test_corrupt_pdf_returns_422(client):
    token, _ = await login_account(client, "google", "x")
    r = await client.post(
        "/api/import/pdf-parse",
        files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422, r.text


async def test_valid_pdf_returns_blocks(client):
    token, _ = await login_account(client, "google", "x")
    r = await client.post(
        "/api/import/pdf-parse",
        files={"file": ("m.pdf", _sample_pdf(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    blocks = r.json()["blocks"]
    by_text = {b["spans"][0]["text"]: b for b in blocks}
    assert by_text["Big Title"]["type"] == "h1"
    assert by_text["First body line here"]["type"] == "p"
