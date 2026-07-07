"""MediaService 단위 테스트 — LocalStorage 백엔드, 반환값·저장 상태로 검증. (juldoc 이식)

variant 리사이징은 저장된 바이트를 Pillow 로 다시 열어 실제 픽셀 치수를 assert 한다.
juldoc 대비: error_code 대신 도메인 MediaError 서브클래스로 검증(HTTP 상태 422 동일).
"""
import pytest

from src.features.doc.application.images import DISPLAY_EDGE, THUMB_EDGE
from src.features.doc.application.media_service import MediaService
from src.features.doc.domain.models import (
    CorruptImage,
    ImageDimensionTooLarge,
    ImageDimensionTooSmall,
    ImageTooLarge,
    UnsupportedImageFormat,
)
from src.features.doc.infrastructure.storage_local import LocalStorage

from ._imgfixtures import (
    dims,
    make_jpeg,
    make_jpeg_with_orientation_and_gps,
    make_png,
)


@pytest.fixture
def service(tmp_path) -> MediaService:
    return MediaService(LocalStorage(tmp_path))


def _key_from_url(url: str) -> str:
    return url.removeprefix("/media/")


class TestUploadHappyPath:
    async def test_valid_png_returns_relative_urls(self, service):
        result = await service.upload(make_png(800, 600, noise=True), "pic.png")
        assert result.url.startswith("/media/")
        assert result.display_url.startswith("/media/")
        assert result.thumb_url.startswith("/media/")
        assert result.content_type == "image/png"
        assert (result.width, result.height) == (800, 600)
        key = _key_from_url(result.url)
        assert len(key) == 64 + len(".png")
        assert key.endswith(".png")

    async def test_valid_jpeg(self, service):
        result = await service.upload(make_jpeg(500, 400), "p.jpg")
        assert result.content_type == "image/jpeg"
        assert _key_from_url(result.url).endswith(".jpg")

    async def test_same_bytes_dedup_same_key(self, service):
        data = make_png(300, 300, noise=True)
        r1 = await service.upload(data, "a.png")
        r2 = await service.upload(data, "b.png")  # 다른 파일명, 같은 바이트
        assert r1.url == r2.url
        assert r1.display_url == r2.display_url
        assert r1.thumb_url == r2.thumb_url

    async def test_variant_keys_share_digest_prefix(self, service):
        result = await service.upload(make_png(400, 400, noise=True), "x.png")
        digest = _key_from_url(result.url).removesuffix(".png")
        assert _key_from_url(result.display_url) == f"{digest}_display.webp"
        assert _key_from_url(result.thumb_url) == f"{digest}_thumb.webp"


class TestVariantResize:
    async def test_large_image_downscaled_to_display_and_thumb(self, service):
        result = await service.upload(make_png(2000, 1500, noise=True), "big.png")
        storage = service.storage
        display = await storage.get(_key_from_url(result.display_url))
        thumb = await storage.get(_key_from_url(result.thumb_url))
        original = await storage.get(_key_from_url(result.url))
        assert dims(display) == (1600, 1200)
        assert dims(thumb) == (320, 240)
        assert dims(original) == (2000, 1500)  # 원본은 그대로
        assert display[:4] == b"RIFF" and display[8:12] == b"WEBP"
        assert len(display) < len(original)

    async def test_small_image_not_upscaled(self, service):
        result = await service.upload(make_png(100, 80, noise=True), "small.png")
        storage = service.storage
        display = await storage.get(_key_from_url(result.display_url))
        thumb = await storage.get(_key_from_url(result.thumb_url))
        assert dims(display) == (100, 80)
        assert dims(thumb) == (100, 80)


class TestExif:
    async def test_orientation_applied_and_gps_stripped(self, service):
        raw = make_jpeg_with_orientation_and_gps(640, 480)
        result = await service.upload(raw, "photo.jpg")
        assert (result.width, result.height) == (480, 640)  # 보정 후 치수 스왑

        storage = service.storage
        display = await storage.get(_key_from_url(result.display_url))
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(display)) as im:
            assert im.height > im.width  # 회전 보정 반영
            assert im.getexif().get(0x8825) is None  # GPS EXIF 제거됨(PII)


class TestSizeBounds:
    async def test_over_10mb_rejected(self, service):
        blob = b"\x89PNG\r\n\x1a\n" + b"\x00" * (10 * 1024 * 1024 + 1)
        with pytest.raises(ImageTooLarge) as exc:
            await service.upload(blob, "big.png")
        assert exc.value.status_code == 422

    async def test_forged_magic_txt_as_png_rejected(self, service):
        with pytest.raises(UnsupportedImageFormat):
            await service.upload(b"totally not an image, just text bytes", "fake.png")

    async def test_shell_under_512b_rejected(self, service):
        shell = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        with pytest.raises(CorruptImage):
            await service.upload(shell, "shell.png")


class TestDimensionBounds:
    async def test_over_4096_rejected(self, service):
        with pytest.raises(ImageDimensionTooLarge):
            await service.upload(make_png(4097, 100), "wide.png")

    async def test_1x1_tracking_pixel_rejected(self, service):
        with pytest.raises(ImageDimensionTooSmall):
            await service.upload(make_png(1, 1), "px.png")

    async def test_16px_rejected(self, service):
        with pytest.raises(ImageDimensionTooSmall):
            await service.upload(make_png(16, 16), "tiny.png")

    async def test_32px_boundary_passes(self, service):
        result = await service.upload(make_png(32, 32, noise=True), "ok.png")
        assert (result.width, result.height) == (32, 32)

    def test_display_edge_constant(self):
        assert DISPLAY_EDGE == 1600 and THUMB_EDGE == 320


class TestDecompressionBomb:
    """거대 이미지 방어 — 치수 선검사가 img.load()(전체 디코드) 전에 거부하는지."""

    async def test_12000px_rejected_before_decode(self, service, monkeypatch):
        data = make_png(12000, 12000)  # 고압축 껍데기(단색)
        assert len(data) < 1024 * 1024

        from PIL import Image

        def _boom(self, *a, **k):
            raise AssertionError("img.load() 도달 — 치수 선검사가 역전됨")

        monkeypatch.setattr(Image.Image, "load", _boom)
        with pytest.raises(ImageDimensionTooLarge):
            await service.upload(data, "bomb.png")

    async def test_decompression_bomb_error_maps_to_422_not_500(self, service, monkeypatch):
        # 방어 심층: 치수 선검사를 우회해도 PIL DecompressionBombError 는 500 아닌 422.
        import src.features.doc.application.images as images_mod

        monkeypatch.setattr(images_mod, "_check_dimensions", lambda w, h: None)
        with pytest.raises(ImageDimensionTooLarge) as exc:
            await service.upload(make_png(15000, 15000), "bomb.png")
        assert exc.value.status_code == 422
