"""이미지 바이트 생성 헬퍼 — doc 미디어 테스트용(test_ 접두 없음 → 수집 안 됨). (juldoc 이식)"""
import io
import os

from PIL import Image


def make_png(width: int, height: int, *, noise: bool = False, color=(30, 60, 90)) -> bytes:
    """RGB PNG 바이트. noise=True 면 랜덤 픽셀(압축 안 됨 → 바이트 커짐, 512B 하한 통과용)."""
    if noise:
        img = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    else:
        img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_jpeg(width: int, height: int, *, color=(200, 40, 40)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def make_jpeg_with_orientation_and_gps(width: int, height: int) -> bytes:
    """orientation=6(90° 회전) + GPS EXIF 를 담은 JPEG. 회전 보정·PII 제거 검증용."""
    img = Image.new("RGB", (width, height), (10, 120, 200))
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate → 표시 시 치수 스왑
    exif[0x8825] = {  # GPS IFD (PII) — 위/경도 RATIONAL(도,분,초)
        1: "N",
        2: (37.0, 30.0, 0.0),
        3: "E",
        4: (127.0, 0.0, 0.0),
    }
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, exif=exif)
    return buf.getvalue()


def dims(data: bytes) -> tuple[int, int]:
    """바이트 → (width, height) (Pillow 로 실제 디코드)."""
    with Image.open(io.BytesIO(data)) as im:
        return im.width, im.height
