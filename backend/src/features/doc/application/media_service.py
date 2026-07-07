"""미디어 유스케이스 계층 — StorageAdapter Protocol 에만 의존. (juldoc features/media/service 이식)

variant 3벌(content-addressed): sha256(원본바이트)를 기준 digest 로,
  original : {digest}{ext}          — 업로드 바이트 그대로.
  display  : {digest}_display.webp  — 최대 변 1600px webp.
  thumb    : {digest}_thumb.webp    — 최대 변 320px webp.
같은 원본 재업로드 → 같은 digest → 세 key 모두 동일 → 멱등 저장(중복 제거).
key 는 전부 단일 세그먼트 basename(슬래시 없음) — 로컬 저장·'/media/{key}' 라우팅 안전.
"""
import hashlib
from dataclasses import dataclass

from src.features.doc.application.images import process_image
from src.features.doc.application.uploads import validate_image
from src.features.doc.domain.storage import StorageAdapter


@dataclass(frozen=True)
class UploadResult:
    """서비스 반환값. 모든 url 은 상대경로 '/media/{key}' (절대 URL 저장 금지).

    width/height 는 orientation 보정 후 원본 치수.
    """

    url: str
    display_url: str
    thumb_url: str
    bytes: int
    content_type: str
    width: int
    height: int


class MediaService:
    def __init__(self, storage: StorageAdapter) -> None:
        self._storage = storage

    @property
    def storage(self) -> StorageAdapter:
        """서빙 엔드포인트(GET /media/{key})가 url_for/get/exists 로 직접 조립할 때 사용."""
        return self._storage

    async def upload(self, data: bytes, filename: str = "") -> UploadResult:
        """검증 → variant 생성 → content-addressed 저장 → 상대 URL 3벌 반환.

        검증 실패는 도메인 MediaError 서브클래스로 전파(→ 422):
          UnsupportedImageFormat(형식/디코드), ImageTooLarge(크기상한),
          ImageDimensionTooLarge(치수상한), ImageDimensionTooSmall(치수하한), CorruptImage(껍데기).
        """
        content_type, ext = validate_image(data, filename)  # 매직바이트 + 10MB 상한
        processed = process_image(data)  # 디코드 + 치수 상·하한 + display/thumb 생성

        digest = hashlib.sha256(data).hexdigest()
        original_key = f"{digest}{ext}"
        await self._storage.put(original_key, data, content_type)

        variant_urls: dict[str, str] = {}
        for variant in processed.variants:
            key = f"{digest}_{variant.suffix}{variant.ext}"
            await self._storage.put(key, variant.data, variant.content_type)
            variant_urls[variant.suffix] = f"/media/{key}"

        return UploadResult(
            url=f"/media/{original_key}",
            display_url=variant_urls["display"],
            thumb_url=variant_urls["thumb"],
            bytes=len(data),
            content_type=content_type,
            width=processed.width,
            height=processed.height,
        )
