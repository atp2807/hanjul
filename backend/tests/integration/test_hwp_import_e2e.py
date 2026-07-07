"""HWP/HWPX 가져오기 E2E — 상태 없는 파싱 엔드포인트(로그인만, book 무관).

미로그인 401 · 손상파일 422(PDF 변환 안내 문구 검증 = 이번 설계 핵심) · 정상 HWPX 200 + 블록.
"""
import pytest
from src.features.auth.domain.models import SocialProfile

from tests.fixtures.hwpx_builder import build_hwpx
from tests.integration.auth_helpers import login_account


@pytest.fixture
def social_profile():
    return SocialProfile("GOOGLE", "hwp-a", "a@x.com", "작가")


async def test_requires_login(client):
    r = await client.post(
        "/api/import/hwp-parse",
        files={"file": ("m.hwpx", build_hwpx(["가"]), "application/hwp+zip")},
    )
    assert r.status_code == 401


async def test_corrupt_file_returns_422_with_pdf_hint(client):
    token, _ = await login_account(client, "google", "a")
    r = await client.post(
        "/api/import/hwp-parse",
        files={"file": ("broken.hwpx", b"not a hwpx", "application/hwp+zip")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422, r.text
    assert "PDF로 변환" in r.json()["detail"]


async def test_valid_hwpx_returns_blocks(client):
    token, _ = await login_account(client, "google", "a")
    r = await client.post(
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
