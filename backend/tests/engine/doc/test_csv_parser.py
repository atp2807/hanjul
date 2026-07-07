from __future__ import annotations

import time
from pathlib import Path

import pytest
from src.engine.doc.models import BlockType
from src.engine.doc.parsers.base import BinaryParser
from src.engine.doc.parsers.csv import CSVParser

REF = Path(__file__).resolve().parent / "reference_data" / "csv"

# reference_data 는 gitignore 대상(로컬 전용) — CI 등 파일 부재 환경에선 skip.
_needs_ref = pytest.mark.skipif(not REF.is_dir(), reason="reference_data/csv not available")


def _table(doc):
    assert len(doc.pages) == 1
    blocks = doc.pages[0].blocks
    assert len(blocks) == 1
    assert blocks[0].type is BlockType.TABLE
    return blocks[0].meta


def test_is_binary_parser() -> None:
    assert isinstance(CSVParser(), BinaryParser)


# ── real-world fixtures (measured) ────────────────────────────


@_needs_ref
def test_nasdaq_real_file_ascii_comma() -> None:
    raw = (REF / "nasdaq_screener_1743910806585.csv").read_bytes()
    meta = _table(CSVParser().parse_bytes(raw))
    # measured header + row count
    assert meta["headers"][0] == "Symbol"
    assert meta["headers"] == [
        "Symbol", "Name", "Last Sale", "Net Change", "% Change",
        "Market Cap", "Country", "IPO Year", "Volume", "Sector", "Industry",
    ]
    assert len(meta["rows"]) == 6896  # 6897 lines - 1 header
    assert meta["rows"][0][0] == "A"
    assert meta["rows"][0][1] == "Agilent Technologies Inc. Common Stock"


@_needs_ref
def test_nts_real_file_cp949_header_korean() -> None:
    """국세청 세무서별 관할구역 — CP949; Korean header must not mojibake."""
    raw = (REF / "국세청_세무서별 관할구역_20220418.csv").read_bytes()
    meta = _table(CSVParser().parse_bytes(raw))
    assert meta["headers"] == [
        "세무서명", "도로명 주소", "우편번호", "전화번호",
        "팩스번호", "세무서코드", "계좌번호", "관할구역",
    ]
    assert len(meta["rows"]) == 137  # 138 lines - 1 header
    assert meta["rows"][0][0] == "서울지방국세청"


@_needs_ref
def test_molit_real_file_cp949_large() -> None:
    """국토교통부 법정동코드 — CP949, 49,862 lines; header Korean, perf sane."""
    raw = (REF / "국토교통부_법정동코드_20250805.csv").read_bytes()
    start = time.perf_counter()
    meta = _table(CSVParser().parse_bytes(raw))
    elapsed = time.perf_counter() - start
    assert meta["headers"] == ["법정동코드", "법정동명", "폐지여부"]
    assert len(meta["rows"]) == 49861  # 49862 lines - 1 header
    assert meta["rows"][0] == ["1100000000", "서울특별시", "존재"]
    assert elapsed < 5.0, f"parse took {elapsed:.2f}s — too slow"


# ── synthetic ─────────────────────────────────────────────────


def test_quoted_fields_with_comma() -> None:
    data = b'a,b\n"Smith, John",42\n'
    meta = _table(CSVParser().parse_bytes(data))
    assert meta["headers"] == ["a", "b"]
    assert meta["rows"] == [["Smith, John", "42"]]


def test_field_with_embedded_newline() -> None:
    data = b'name,note\n"line1\nline2",ok\n'
    meta = _table(CSVParser().parse_bytes(data))
    assert meta["rows"] == [["line1\nline2", "ok"]]


def test_empty_file() -> None:
    doc = CSVParser().parse_bytes(b"")
    assert doc.pages == []
    assert doc.metadata == {}


def test_whitespace_only_file() -> None:
    doc = CSVParser().parse_bytes(b"\n\n  \n")
    assert doc.pages == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
