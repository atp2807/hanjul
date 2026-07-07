"""HWP/HWPX 가져오기 파서 단위 테스트 — 즉석 HWPX 버퍼로 실제 파싱까지 검증."""
import pytest
from src.engine.imports.hwp_import import InvalidHwpFile, hwp_to_neutral_blocks

from tests.fixtures.hwpx_builder import build_hwpx


def test_hwpx_to_three_p_blocks():
    data = build_hwpx(["첫 문단입니다", "둘째 문단입니다", "셋째"])
    blocks = hwp_to_neutral_blocks(data, "manuscript.hwpx")

    assert blocks == [
        {"type": "p", "spans": [{"text": "첫 문단입니다", "marks": []}]},
        {"type": "p", "spans": [{"text": "둘째 문단입니다", "marks": []}]},
        {"type": "p", "spans": [{"text": "셋째", "marks": []}]},
    ]


def test_corrupt_bytes_raise_invalid_with_pdf_hint():
    with pytest.raises(InvalidHwpFile) as exc:
        hwp_to_neutral_blocks(b"not a hwpx", "broken.hwpx")
    assert "PDF" in exc.value.detail
    assert exc.value.status_code == 422
