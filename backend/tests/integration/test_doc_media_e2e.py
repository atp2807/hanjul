"""미디어 엔드포인트 E2E — httpx, get_media_service 를 tmp LocalStorage 로 오버라이드. (juldoc 이식)

juldoc 대비: 응답 필드 camelCase(displayUrl·thumbUrl·contentType), 본문 크기 상한은
BodySizeLimit 미들웨어가 아니라 엔드포인트 len 검사 → 413(books import 관례),
에러 바디는 {"detail": …}(error_code 없음). 최종 경로는 /api/media(·/{key}).
"""
import io

import httpx
import pytest

from src.config.settings import settings

settings.DEBUG = False

from main import app  # noqa: E402
from src.features.doc.application.media_service import MediaService  # noqa: E402
from src.features.doc.infrastructure.storage_local import LocalStorage  # noqa: E402
from src.features.doc.presentation.dependencies import get_media_service  # noqa: E402

from tests.features.doc._imgfixtures import make_png  # noqa: E402


@pytest.fixture
def media(tmp_path):
    # 업로드·서빙이 같은 저장소를 보도록 단일 인스턴스를 주입(디스크 격리 = tmp_path).
    service = MediaService(LocalStorage(tmp_path))
    app.dependency_overrides[get_media_service] = lambda: service
    yield
    app.dependency_overrides.clear()


async def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


class TestUploadEndpoint:
    async def test_post_media_returns_201_and_contract(self, media):
        data = make_png(600, 400, noise=True)
        async with await _client() as c:
            resp = await c.post(
                "/api/media", files={"file": ("pic.png", io.BytesIO(data), "image/png")}
            )
        assert resp.status_code == 201
        body = resp.json()
        assert set(body) == {
            "url", "displayUrl", "thumbUrl", "bytes", "contentType", "width", "height"
        }
        assert body["url"].startswith("/media/")
        assert body["displayUrl"].startswith("/media/")
        assert body["thumbUrl"].startswith("/media/")
        assert body["contentType"] == "image/png"
        assert body["bytes"] == len(data)
        assert (body["width"], body["height"]) == (600, 400)

    async def test_get_media_serves_original_bytes(self, media):
        data = make_png(300, 200, noise=True)
        async with await _client() as c:
            post = await c.post(
                "/api/media", files={"file": ("p.png", io.BytesIO(data), "image/png")}
            )
            url = post.json()["url"]
            got = await c.get(f"/api{url}")  # /media/{key} → /api/media/{key}
        assert got.status_code == 200
        assert got.content == data  # 로컬 폴백: 원본 바이트 그대로 프록시

    async def test_get_display_variant_is_webp(self, media):
        data = make_png(800, 600, noise=True)
        async with await _client() as c:
            post = await c.post(
                "/api/media", files={"file": ("p.png", io.BytesIO(data), "image/png")}
            )
            display_url = post.json()["displayUrl"]
            got = await c.get(f"/api{display_url}")
        assert got.status_code == 200
        assert got.content[:4] == b"RIFF" and got.content[8:12] == b"WEBP"

    async def test_get_missing_key_404(self, media):
        async with await _client() as c:
            resp = await c.get("/api/media/" + "0" * 64 + ".png")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    async def test_forged_upload_422(self, media):
        async with await _client() as c:
            resp = await c.post(
                "/api/media", files={"file": ("fake.png", io.BytesIO(b"not an image"), "image/png")}
            )
        assert resp.status_code == 422

    async def test_decompression_bomb_returns_422_not_500(self, media):
        data = make_png(15000, 15000)  # 종전 img.load() 에서 500 나던 경로 → 이제 422
        async with await _client() as c:
            resp = await c.post(
                "/api/media", files={"file": ("bomb.png", io.BytesIO(data), "image/png")}
            )
        assert resp.status_code == 422

    async def test_over_max_edge_returns_422(self, media):
        data = make_png(4097, 100)
        async with await _client() as c:
            resp = await c.post(
                "/api/media", files={"file": ("wide.png", io.BytesIO(data), "image/png")}
            )
        assert resp.status_code == 422

    async def test_over_body_size_limit_returns_413(self, media):
        # 12MB 초과 요청은 엔드포인트 len 검사가 413 으로 막는다(books import 관례).
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (12 * 1024 * 1024 + 4096)
        async with await _client() as c:
            resp = await c.post(
                "/api/media", files={"file": ("huge.png", io.BytesIO(oversized), "image/png")}
            )
        assert resp.status_code == 413
