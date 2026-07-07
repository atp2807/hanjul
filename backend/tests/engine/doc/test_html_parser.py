from __future__ import annotations

from pathlib import Path

import pytest
from src.engine.doc.models import BlockType, UniversalDoc
from src.engine.doc.parsers.base import BinaryParser
from src.engine.doc.parsers.html import HTMLParser, _decode_html, _meta_charset

REF = Path(__file__).resolve().parent / "reference_data" / "html"

# reference_data 는 gitignore 대상(로컬 전용) — CI 등 파일 부재 환경에선 skip.
_needs_ref = pytest.mark.skipif(not REF.is_dir(), reason="reference_data/html not available")


def _all_text(doc: UniversalDoc) -> str:
    return " ".join(b.content for p in doc.pages for b in p.blocks)


def test_is_binary_parser() -> None:
    assert isinstance(HTMLParser(), BinaryParser)


# ── real-world fixtures (measured) ────────────────────────────


@_needs_ref
def test_mohadus_real_file() -> None:
    raw = (REF / "mohadus_db_diagram.html").read_bytes()
    doc = HTMLParser().parse_bytes(raw)
    assert doc.pages, "expected at least one page"
    text = _all_text(doc)
    # measured: heading '🎯 MOHADUS DB 설계도' + Korean body text survive
    assert "MOHADUS DB 설계도" in text
    assert "프로모터" in text
    assert any(b.type is BlockType.HEADING for b in doc.pages[0].blocks)


@_needs_ref
def test_preview_real_file() -> None:
    raw = (REF / "Preview.html").read_bytes()
    doc = HTMLParser().parse_bytes(raw)
    text = _all_text(doc)
    assert "Tutorial" in text
    # Preview.html contains a real <table> → a TABLE block
    assert any(b.type is BlockType.TABLE for b in doc.pages[0].blocks)


@_needs_ref
def test_kepco_real_file_long_line_and_script_sanitized() -> None:
    """KEPCO secure mail: 8,393-char line is inside <script>; must be dropped."""
    raw = (REF / "[한국전력]보안메일.html").read_bytes()
    doc = HTMLParser().parse_bytes(raw)
    text = _all_text(doc)
    assert "한국전력" in text
    assert "보안메일입니다" in text  # measured body sentence survives
    # script sanitation is inherited from parse_dialect: JS crypto body is gone.
    assert "typeof x" not in text
    assert "function(" not in text


# ── encoding decision ─────────────────────────────────────────


def test_meta_charset_detected() -> None:
    assert _meta_charset(b'<html><head><meta charset="EUC-KR"></head>') == "euc-kr"
    assert (
        _meta_charset(
            b'<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        )
        == "utf-8"
    )
    assert _meta_charset(b"<html><head></head>") is None


def test_meta_charset_ignored_in_body() -> None:
    # A charset= inside body text after </head> must not hijack the scan.
    html = b"<head></head><body>charset=euc-kr free text</body>"
    assert _meta_charset(html) is None


def test_utf8_bom_stripped() -> None:
    raw = b"\xef\xbb\xbf" + "<p>안녕</p>".encode()
    text = _decode_html(raw)
    assert text.startswith("<p>")  # BOM removed
    assert "안녕" in text


def test_cp949_fallback_when_undeclared() -> None:
    # Korean bytes, no charset declared, invalid as utf-8 → cp949 fallback.
    raw = "<p>세무서</p>".encode("cp949")
    text = _decode_html(raw)
    assert "세무서" in text


def test_declared_charset_used() -> None:
    raw = '<head><meta charset="euc-kr"></head><body><p>세무서</p></body>'.encode("cp949")
    doc = HTMLParser().parse_bytes(raw)
    assert "세무서" in _all_text(doc)


def test_empty_input() -> None:
    doc = HTMLParser().parse_bytes(b"")
    assert doc.pages == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
