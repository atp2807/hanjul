"""이미지 업로드 검증 — 매직바이트 화이트리스트가 정본이다. (juldoc shared/upload.py 이식)

content-type 헤더는 클라이언트가 위조할 수 있으므로 절대 신뢰하지 않는다. 확장자도
파일명(위조 가능)이 아니라 매직바이트에서 도출한다 — 그래야 content-addressed key
(sha256+ext)가 실제 내용과 일치한다.

juldoc 대비: error_code(MEDIA_001/002) 대신 도메인 서브클래스(UnsupportedImageFormat·
ImageTooLarge)를 던진다. HTTP 상태(422)는 동일.
"""
import hashlib

from src.features.doc.domain.models import ImageTooLarge, UnsupportedImageFormat

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB

# (매직 프리픽스, content-type, 확장자). WEBP 는 프리픽스로 못 잡아 아래서 특수 처리.
_MAGIC_TABLE: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"GIF8", "image/gif", ".gif"),
]

# 확장자 → content-type (로컬 폴백 서빙 시 key 확장자에서 복원).
_EXT_CONTENT_TYPE: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _detect(data: bytes) -> tuple[str, str] | None:
    """매직바이트 → (content_type, ext). 못 맞추면 None."""
    for magic, content_type, ext in _MAGIC_TABLE:
        if data.startswith(magic):
            return content_type, ext
    # WEBP: RIFF....WEBP (0:4 == RIFF, 8:12 == WEBP)
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def validate_image(data: bytes, filename: str = "") -> tuple[str, str]:
    """이미지 바이트 검증 → (content_type, ext). filename 은 신뢰하지 않는다.

    크기 초과 → ImageTooLarge(422), 매직바이트 불일치 → UnsupportedImageFormat(422).
    반환 ext 는 매직바이트에서 도출(파일명 무시) — content-addressed key 재료.
    """
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageTooLarge(
            f"이미지 크기가 {MAX_IMAGE_BYTES // (1024 * 1024)}MB를 초과했어요."
        )
    detected = _detect(data)
    if detected is None:
        raise UnsupportedImageFormat()
    return detected


def sha256_key(data: bytes, ext: str) -> str:
    """content-addressed 오브젝트 key = sha256(bytes) + 확장자.

    같은 바이트 → 같은 key → 재업로드 시 중복 제거(동일 오브젝트).
    """
    return hashlib.sha256(data).hexdigest() + ext


def content_type_for_key(key: str) -> str:
    """key 확장자 → content-type (로컬 폴백 서빙 시). 모르면 octet-stream."""
    for ext, content_type in _EXT_CONTENT_TYPE.items():
        if key.endswith(ext):
            return content_type
    return "application/octet-stream"
