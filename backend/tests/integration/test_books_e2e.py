"""HTTP → 서비스 → 실 레포 → SQLite 전 계층 E2E (httpx ASGITransport).

get_session 의존성을 SQLite 세션으로 오버라이드 → 진짜 DB 에 대해 엔드포인트를 검증.
모두 한 이벤트 루프(pytest-asyncio)에서 돌아 async 루프 충돌이 없다.
"""
import httpx
import pytest

from src.config.settings import settings

settings.DEBUG = False  # lifespan 의 엔진 생성 회피

from main import app  # noqa: E402
from src.config.database import get_session  # noqa: E402


@pytest.fixture
def override_db(sessionmaker):
    async def _get_session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
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


async def test_import_unknown_book_404_over_http(override_db):
    import uuid
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.post(f"/api/books/{uuid.uuid4()}/import", json={"rawText": "x"})
        assert r.status_code == 404
