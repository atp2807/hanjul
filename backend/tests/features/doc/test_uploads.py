"""validate_image 매직바이트 테이블 + key 헬퍼 단위 테스트. (juldoc shared/upload 이식)

content-type 헤더/파일명을 신뢰하지 않고 매직바이트만으로 형식을 판정하는지 검증.
"""
import pytest

from src.features.doc.application.uploads import (
    MAX_IMAGE_BYTES,
    content_type_for_key,
    sha256_key,
    validate_image,
)
from src.features.doc.domain.models import ImageTooLarge, UnsupportedImageFormat


class TestMagicTable:
    def test_jpeg_magic(self):
        assert validate_image(b"\xff\xd8\xff" + b"\x00" * 32) == ("image/jpeg", ".jpg")

    def test_png_magic(self):
        assert validate_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32) == ("image/png", ".png")

    def test_gif_magic(self):
        assert validate_image(b"GIF89a" + b"\x00" * 32) == ("image/gif", ".gif")

    def test_webp_magic(self):
        data = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32
        assert validate_image(data) == ("image/webp", ".webp")

    def test_filename_and_content_type_header_are_ignored(self):
        # 파일명이 .png 라도 매직이 JPEG 면 JPEG 로 판정(파일명 불신).
        assert validate_image(b"\xff\xd8\xff\x00\x00", "evil.png") == ("image/jpeg", ".jpg")

    def test_unknown_magic_rejected(self):
        with pytest.raises(UnsupportedImageFormat) as exc:
            validate_image(b"this is plain text, not an image at all")
        assert exc.value.status_code == 422

    def test_oversize_rejected(self):
        with pytest.raises(ImageTooLarge):
            validate_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_BYTES + 1))


class TestKeyHelpers:
    def test_sha256_key_deterministic_with_ext(self):
        k1 = sha256_key(b"hello", ".png")
        k2 = sha256_key(b"hello", ".png")
        assert k1 == k2
        assert k1 == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824.png"
        )

    def test_different_bytes_different_key(self):
        assert sha256_key(b"a", ".png") != sha256_key(b"b", ".png")

    def test_content_type_for_key(self):
        assert content_type_for_key("abc.png") == "image/png"
        assert content_type_for_key("abc.jpg") == "image/jpeg"
        assert content_type_for_key("abc_display.webp") == "image/webp"
        assert content_type_for_key("abc.unknown") == "application/octet-stream"
