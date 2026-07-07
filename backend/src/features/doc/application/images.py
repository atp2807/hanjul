"""이미지 디코드 + variant 생성 파이프라인 (Pillow). (juldoc features/media/images.py 이식)

검증 이중화: uploads.validate_image 가 매직바이트·바이트상한을 먼저 거른 뒤, 여기서
실제 디코드해 치수 상·하한을 판정한다 — 매직만 맞는 껍데기/추적픽셀 차단.

variant 3벌:
  original : 업로드 바이트 그대로(서비스가 저장). 여기선 치수 판정만.
  display  : 최대 변 1600px webp(q85) — 문서 본문용.
  thumb    : 최대 변 320px webp — 목록/미리보기용.
EXIF: 로드 시 orientation 적용(회전 보정), variant 는 webp 재인코딩하며 EXIF 미첨부
      → GPS 등 PII 자동 소거. (원본은 서비스가 바이트 그대로 저장 — 아카이브.)

juldoc 대비: error_code(MEDIA_003/004/005/001) 대신 도메인 서브클래스
(ImageDimensionTooLarge·ImageDimensionTooSmall·CorruptImage·UnsupportedImageFormat).
상태(모두 422)는 동일 — 특히 DecompressionBombError 가 500 으로 새지 않고 422 로 흡수됨.
"""
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from src.features.doc.domain.models import (
    CorruptImage,
    ImageDimensionTooLarge,
    ImageDimensionTooSmall,
    UnsupportedImageFormat,
)

MAX_EDGE = 4096      # 최대 변 상한(초과 거부)
MIN_EDGE = 32        # 최소 변 하한(미만 거부) — 추적픽셀/아이콘파편 차단(주 방어선)
MIN_BYTES = 512      # 파일 크기 하한(미만+디코드실패 = 껍데기)
DISPLAY_EDGE = 1600
THUMB_EDGE = 320
WEBP_QUALITY = 85


@dataclass(frozen=True)
class Variant:
    """생성된 variant 오브젝트. suffix 는 key 접미(_display/_thumb)."""

    suffix: str
    data: bytes
    content_type: str
    ext: str


@dataclass(frozen=True)
class ProcessedImage:
    """디코드 결과. width/height 는 orientation 보정 후 원본 치수."""

    width: int
    height: int
    variants: list[Variant]


def _check_dimensions(width: int, height: int) -> None:
    """치수 상·하한 판정. 상한 초과 ImageDimensionTooLarge, 하한 미만 ImageDimensionTooSmall.

    _load 가 img.load()(전체 픽셀 디코드) '전에' 헤더 치수로 먼저 호출한다 —
    거대 이미지를 메모리에 풀지 않고 거부해 decompression bomb 자원낭비를 회피한다.
    """
    if max(width, height) > MAX_EDGE:
        raise ImageDimensionTooLarge(f"이미지 최대 변이 {MAX_EDGE}px를 초과했어요.")
    if min(width, height) < MIN_EDGE:
        raise ImageDimensionTooSmall(f"이미지가 너무 작아요. (최소 변 {MIN_EDGE}px 필요)")


def _load(data: bytes) -> Image.Image:
    """바이트 → Pillow 이미지. EXIF orientation 적용(반환 이미지엔 EXIF 미포함).

    디코드 순서가 핵심이다: Image.open()(헤더만 파싱) 직후 치수를 선검사해, 상·하한
    위반이면 img.load()(전체 픽셀 디코드) 전에 거부한다 — 12000px 고압축 껍데기가
    1GB+ RSS 를 먹는 걸 막는다.

    실패 매핑(모두 422, 절대 500 금지):
      - 치수 위반: ImageDimensionTooLarge(상한)/ImageDimensionTooSmall(하한).
      - DecompressionBombError(Exception 직접 상속 → 아래 일반 except 에 안 잡힘):
        헤더 치수 선검사가 먼저 걸리지만, 방어적으로 여기서도 잡아 ImageDimensionTooLarge.
      - 디코드 실패(껍데기/손상): MIN_BYTES 미만 CorruptImage, 아니면 UnsupportedImageFormat.
    """
    try:
        img = Image.open(io.BytesIO(data))
        _check_dimensions(img.width, img.height)  # img.load() 전 헤더 치수로 판정
        img.load()  # 지연 디코드 강제 — truncated/껍데기를 여기서 잡는다.
    except Image.DecompressionBombError as e:
        raise ImageDimensionTooLarge(f"이미지 최대 변이 {MAX_EDGE}px를 초과했어요.") from e
    except (UnidentifiedImageError, OSError, ValueError) as e:
        if len(data) < MIN_BYTES:
            raise CorruptImage() from e
        raise UnsupportedImageFormat("이미지를 디코드할 수 없어요.") from e
    # exif_transpose: orientation 태그대로 회전/반전 적용한 새 이미지(EXIF 없음) 반환.
    return ImageOps.exif_transpose(img) or img


def _webp_variant(img: Image.Image, suffix: str, edge: int) -> Variant:
    """이미지를 최대 변 edge 로 축소(작으면 그대로) 후 webp 재인코딩. EXIF 미첨부."""
    im = img.copy()
    # webp 인코딩 가능 모드로 정규화 — 팔레트/CMYK 등은 변환(투명 보존).
    if im.mode in ("P", "LA"):
        im = im.convert("RGBA")
    elif im.mode == "CMYK":
        im = im.convert("RGB")
    # thumbnail 은 종횡비 유지 + 축소 전용(업스케일 안 함). 이미 작으면 무변.
    im.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)  # exif= 미전달 → PII 소거
    return Variant(suffix=suffix, data=buf.getvalue(), content_type="image/webp", ext=".webp")


def process_image(data: bytes) -> ProcessedImage:
    """디코드(치수 선검사 포함) → display/thumb variant 생성.

    치수 상·하한 판정은 _load 가 img.load() '전에' 수행한다 — 거대 이미지를 디코드하지
    않고 거부. 애니메이션 GIF 는 첫 프레임만 variant 로 삼는다(원본은 서비스가 전체 저장).
    """
    img = _load(data)
    return ProcessedImage(
        width=img.width,
        height=img.height,
        variants=[
            _webp_variant(img, "display", DISPLAY_EDGE),
            _webp_variant(img, "thumb", THUMB_EDGE),
        ],
    )
