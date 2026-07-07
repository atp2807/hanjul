"""HTTP → 서비스 → 실 레포 → SQLite 전 계층 E2E (httpx ASGITransport).

get_session 의존성을 SQLite 세션으로 오버라이드 → 진짜 DB 에 대해 엔드포인트를 검증.
모두 한 이벤트 루프(pytest-asyncio)에서 돌아 async 루프 충돌이 없다.
"""
import httpx
import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings

settings.DEBUG = False  # lifespan 의 엔진 생성 회피

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402
from src.features.auth.application.auth_service import AuthService  # noqa: E402
from src.features.auth.domain.models import SocialProfile  # noqa: E402
from src.features.auth.infrastructure.account_repo import SqlAccountRepository  # noqa: E402
from src.features.auth.presentation.dependencies import (  # noqa: E402
    get_auth_service,
    token_issuer,
)

from tests.fixtures.fake_account_repo import FakeProvider  # noqa: E402
from tests.integration.auth_helpers import login_account  # noqa: E402

_PROFILE = SocialProfile("GOOGLE", "author-x", "a@x.com", "작가")


@pytest.fixture
def override_db(sessionmaker):
    async def _get_session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def app_db(sessionmaker):
    async def _session():
        async with sessionmaker() as s:
            yield s

    def _auth(session: AsyncSession = Depends(get_session)):
        return AuthService(
            SqlAccountRepository(session), {"GOOGLE": FakeProvider("GOOGLE", _PROFILE)}, token_issuer()
        )

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_auth_service] = _auth
    yield
    app.dependency_overrides.clear()


async def test_import_then_read_via_http(override_db):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        # 1) 책 생성
        r = await client.post("/api/books", json={"title": "한 줄", "kind": "BOOK"})
        assert r.status_code == 201
        book_id = r.json()["bookId"]

        # 2) 원고 import (TXT/MD → 정본 HTML)
        raw = "# 1장\n\n베스트셀러인데 왜 작가는 돈을 못 벌까.\n\n> 명언"
        imp = await client.post(f"/api/books/{book_id}/import", json={"rawText": raw})
        assert imp.status_code == 200
        assert imp.json()["blockCount"] == 3  # H1 + P + QUOTE

        # 3) 정본 조회 (리더가 소비할 형태)
        content = (await client.get(f"/api/books/{book_id}/content")).json()
        assert content["title"] == "한 줄"
        blocks = content["chapters"][0]["blocks"]
        assert [b["blockType"] for b in blocks] == ["H1", "P", "QUOTE"]
        assert blocks[0]["html"] == "<h1>1장</h1>"


async def test_set_content_rejects_malicious_html_and_rolls_back(app_db):
    """PUT /content 는 정본 문법만 허용 — 악성 html 이 섞이면 422 + 전체 롤백."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        token, _ = await login_account(c, "google", "x")
        auth = {"Authorization": f"Bearer {token}"}
        book = (await c.post("/api/books", json={"title": "내 책"}, headers=auth)).json()["bookId"]

        # (a) 정상 정본 블록 → 204, 저장 확인
        good = {
            "chapters": [
                {"title": "1장", "blocks": [
                    {"type": "H1", "html": "<h1>제목</h1>"},
                    {"type": "P", "html": "<p>본문 <strong>굵게</strong>.</p>"},
                ]},
            ]
        }
        assert (await c.put(f"/api/books/{book}/content", json=good, headers=auth)).status_code == 204
        blocks = (await c.get(f"/api/books/{book}/content")).json()["chapters"][0]["blocks"]
        assert [b["html"] for b in blocks] == ["<h1>제목</h1>", "<p>본문 <strong>굵게</strong>.</p>"]

        # (b) 악성 html 이 섞인 요청 → 422 + 앞의 정상 블록도 저장 안 됨(전체 롤백)
        evil = {
            "chapters": [
                {"title": "2장", "blocks": [
                    {"type": "P", "html": "<p>정상 문단</p>"},
                    {"type": "P", "html": "<p><script>alert(1)</script></p>"},
                ]},
            ]
        }
        assert (await c.put(f"/api/books/{book}/content", json=evil, headers=auth)).status_code == 422
        # 기존 정본이 그대로 유지(악성 요청이 부분 저장·덮어쓰기 안 함)
        after = (await c.get(f"/api/books/{book}/content")).json()["chapters"][0]["blocks"]
        assert [b["html"] for b in after] == ["<h1>제목</h1>", "<p>본문 <strong>굵게</strong>.</p>"]


async def test_import_unknown_book_404_over_http(override_db):
    import uuid
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.post(f"/api/books/{uuid.uuid4()}/import", json={"rawText": "x"})
        assert r.status_code == 404
