"""Tests for the HWPX (open OWPML) parser.

Reference-file assertions use cell texts measured directly from the sample
documents in ``reference_data/hwpx/`` — not invented.  Synthetic zip fixtures
cover the empty / malformed-mimetype / non-zip edge cases without needing the
(large, government-issued) reference files.
"""
from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from src.engine.doc.models import BlockType, UniversalDoc
from src.engine.doc.parsers.base import BinaryParser
from src.engine.doc.parsers.hwpx import HWPXParser

REFERENCE_DIR = Path(__file__).resolve().parent / "reference_data" / "hwpx"
REF_GU = REFERENCE_DIR / "(별첨2) [별표 1] 구의 명칭과 관할구역.hwpx"
REF_RI = REFERENCE_DIR / "(별첨3) [별표 1의2] 읍ㆍ면ㆍ리의 명칭 및 관할구역.hwpx"
REF_CHANGE = REFERENCE_DIR / (
    "★[붙임] 행정기관(행정동) 및 관할구역(법정동) 변경내역(경기도 화성시).hwpx"
)

_NS_PARAGRAPH = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_NS_SECTION = "http://www.hancom.co.kr/hwpml/2011/section"


# ── Synthetic container helpers ────────────────────────────────


def _make_hwpx(sections: dict[str, str], mimetype: str = "application/hwp+zip") -> bytes:
    """Build a minimal in-memory HWPX zip from section-name -> XML mappings."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", mimetype)
        for name, xml in sections.items():
            zf.writestr(name, xml)
    return buf.getvalue()


_EMPTY_SECTION = (
    f'<hs:sec xmlns:hs="{_NS_SECTION}" xmlns:hp="{_NS_PARAGRAPH}"></hs:sec>'
)


def _all_blocks(doc: UniversalDoc):
    return [b for page in doc.pages for b in page.blocks]


def _tables(doc: UniversalDoc):
    return [b for b in _all_blocks(doc) if b.type == BlockType.TABLE]


def _find_cell(table_block, row: int, col: int) -> dict:
    for cell in table_block.meta["cells"]:
        if cell["row"] == row and cell["col"] == col:
            return cell
    raise AssertionError(f"no cell at r{row}c{col}")


# ── Protocol conformance ───────────────────────────────────────


class TestHWPXProtocol:
    def test_implements_binary_parser(self):
        assert isinstance(HWPXParser(), BinaryParser)

    def test_has_parse_bytes_method(self):
        assert callable(getattr(HWPXParser(), "parse_bytes", None))


# ── Edge cases (synthetic) ─────────────────────────────────────


class TestHWPXEdgeCases:
    def test_non_zip_bytes_raises(self):
        with pytest.raises(ValueError):
            HWPXParser().parse_bytes(b"this is not a zip file")

    def test_empty_bytes_raises(self):
        with pytest.raises(ValueError):
            HWPXParser().parse_bytes(b"")

    def test_wrong_mimetype_raises(self):
        data = _make_hwpx(
            {"Contents/section0.xml": _EMPTY_SECTION},
            mimetype="application/zip",
        )
        with pytest.raises(ValueError):
            HWPXParser().parse_bytes(data)

    def test_missing_mimetype_raises(self):
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Contents/section0.xml", _EMPTY_SECTION)
        with pytest.raises(ValueError):
            HWPXParser().parse_bytes(buf.getvalue())

    def test_empty_document_parses_to_blank_page(self):
        data = _make_hwpx({"Contents/section0.xml": _EMPTY_SECTION})
        doc = HWPXParser().parse_bytes(data)
        assert isinstance(doc, UniversalDoc)
        assert len(doc.pages) == 1
        assert doc.pages[0].blocks == []

    def test_encrypted_document_raises(self):
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("mimetype", "application/hwp+zip")
            zf.writestr(
                "META-INF/manifest.xml",
                '<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument'
                ':xmlns:manifest:1.0"><odf:encryption-data/></odf:manifest>',
            )
            zf.writestr("Contents/section0.xml", _EMPTY_SECTION)
        with pytest.raises(ValueError):
            HWPXParser().parse_bytes(buf.getvalue())


# ── Synthetic table parsing ────────────────────────────────────


class TestHWPXSyntheticTable:
    def test_table_and_paragraph_extracted(self):
        section = (
            f'<hs:sec xmlns:hs="{_NS_SECTION}" xmlns:hp="{_NS_PARAGRAPH}">'
            '<hp:p><hp:run><hp:t>제목 문단</hp:t></hp:run></hp:p>'
            '<hp:p><hp:run><hp:tbl rowCnt="1" colCnt="2">'
            '<hp:tr>'
            '<hp:tc><hp:subList><hp:p><hp:run><hp:t>가</hp:t></hp:run></hp:p>'
            '</hp:subList><hp:cellAddr colAddr="0" rowAddr="0"/>'
            '<hp:cellSpan colSpan="1" rowSpan="1"/>'
            '<hp:cellSz width="7200" height="3600"/></hp:tc>'
            '<hp:tc><hp:subList><hp:p><hp:run><hp:t>나</hp:t></hp:run></hp:p>'
            '</hp:subList><hp:cellAddr colAddr="1" rowAddr="0"/>'
            '<hp:cellSpan colSpan="1" rowSpan="1"/>'
            '<hp:cellSz width="7200" height="3600"/></hp:tc>'
            '</hp:tr></hp:tbl></hp:run></hp:p>'
            "</hs:sec>"
        )
        doc = HWPXParser().parse_bytes(_make_hwpx({"Contents/section0.xml": section}))
        blocks = _all_blocks(doc)
        assert blocks[0].type == BlockType.PARAGRAPH
        assert blocks[0].content == "제목 문단"

        tables = _tables(doc)
        assert len(tables) == 1
        table = tables[0]
        assert table.meta["row_count"] == 1
        assert table.meta["col_count"] == 2
        assert table.meta["rows"] == [["가", "나"]]
        # cell width 7200 HWPUNIT == 1 inch == 25.4 mm
        assert _find_cell(table, 0, 0)["width_mm"] == 25.4


# ── Reference files (measured ground truth) ────────────────────


@pytest.mark.skipif(not REF_GU.exists(), reason="reference HWPX not available")
class TestReferenceGuTable:
    """(별첨2) 구의 명칭과 관할구역 — single 5x2 table."""

    @pytest.fixture(scope="class")
    def doc(self):
        return HWPXParser().parse_bytes(REF_GU.read_bytes())

    def test_parses_to_universal_doc(self, doc):
        assert isinstance(doc, UniversalDoc)
        assert len(doc.pages) == 1

    def test_has_table_block(self, doc):
        tables = _tables(doc)
        assert len(tables) == 1
        assert tables[0].meta["row_count"] == 5
        assert tables[0].meta["col_count"] == 2

    def test_header_cell_texts(self, doc):
        table = _tables(doc)[0]
        assert _find_cell(table, 0, 0)["text"] == "구의 명칭"
        assert _find_cell(table, 0, 1)["text"] == "관할구역"

    def test_body_cell_texts(self, doc):
        table = _tables(doc)[0]
        assert _find_cell(table, 1, 0)["text"] == "만세구"
        assert _find_cell(table, 1, 1)["text"] == (
            "우정읍, 향남읍, 남양읍, 마도면, 송산면,서신면, 팔탄면, "
            "장안면, 양감면 및 새솔동 일원"
        )

    def test_page_layout_a4(self, doc):
        layout = doc.metadata["page_layout"]
        assert layout["width_mm"] == 210.0
        assert layout["height_mm"] == 297.0


@pytest.mark.skipif(not REF_RI.exists(), reason="reference HWPX not available")
class TestReferenceRiTable:
    """(별첨3) 읍ㆍ면ㆍ리 — single large 170x3 table."""

    @pytest.fixture(scope="class")
    def doc(self):
        return HWPXParser().parse_bytes(REF_RI.read_bytes())

    def test_has_large_table(self, doc):
        tables = _tables(doc)
        assert len(tables) == 1
        assert tables[0].meta["row_count"] == 170
        assert tables[0].meta["col_count"] == 3

    def test_header_row_texts(self, doc):
        table = _tables(doc)[0]
        assert _find_cell(table, 0, 0)["text"] == "읍 ․ 면"
        assert _find_cell(table, 0, 1)["text"] == "리 명 칭"
        assert _find_cell(table, 0, 2)["text"] == "관 할 구 역"

    def test_first_body_row_texts(self, doc):
        table = _tables(doc)[0]
        assert _find_cell(table, 1, 0)["text"] == "봉 담 읍"
        assert _find_cell(table, 1, 1)["text"] == "상 리"
        assert _find_cell(table, 1, 2)["text"] == "상    리 일원"


@pytest.mark.skipif(not REF_CHANGE.exists(), reason="reference HWPX not available")
class TestReferenceChangeTables:
    """★[붙임] 변경내역 — multiple tables, with merged (spanned) cells."""

    @pytest.fixture(scope="class")
    def doc(self):
        return HWPXParser().parse_bytes(REF_CHANGE.read_bytes())

    def test_has_multiple_tables(self, doc):
        assert len(_tables(doc)) == 4

    def test_notice_table_text(self, doc):
        first = _tables(doc)[0]
        assert first.meta["row_count"] == 1
        assert first.meta["col_count"] == 1
        assert _find_cell(first, 0, 0)["text"].startswith("✔안내사항")

    def test_merged_cell_spans(self, doc):
        # tbl index 2 (11-col header) carries the merged cells.
        table = _tables(doc)[2]
        assert table.meta["col_count"] == 11

        title = _find_cell(table, 0, 0)
        assert title["text"] == "기관명(A열)"
        assert title["rowspan"] == 3

        before = _find_cell(table, 0, 1)
        assert before["text"] == "변경 전"
        assert before["colspan"] == 3

        after = _find_cell(table, 0, 4)
        assert after["text"] == "변경 후"
        assert after["colspan"] == 7
